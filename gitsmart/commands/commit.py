import sys
from pathlib import Path

import click
from git import GitCommandError, InvalidGitRepositoryError, Repo
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gitsmart.client import GitSmartAPIError, GitSmartClient
from gitsmart.config import get_api_key, get_commit_language, TIMEOUT_COMMIT, TIMEOUT_COMMIT_SMART
from gitsmart.lang import is_valid_language

console = Console()

DIFF_MAX_CHARS = 100_000
SMART_MAX_FILES = 50


@click.command()
@click.option("--auto", is_flag=True, help="Commit without confirmation.")
@click.option("--smart", is_flag=True, help="Analyze and group staged files into multiple logical commits.")
@click.option(
    "--type",
    "commit_type",
    default=None,
    metavar="TYPE",
    help="Force commit type (feat/fix/docs/refactor/etc.).",
)
@click.option(
    "--lang",
    "lang",
    default=None,
    metavar="LANG",
    help="Commit message language (ISO 639-1), overrides config.",
)
@click.option("--short", "length", flag_value="short", default=True, help="Generate concise commit message (default).")
@click.option("--detail", "length", flag_value="detail", help="Generate detailed commit message with full body.")
def commit(auto, smart, commit_type, lang, length):
    """Generate AI commit message from staged changes."""
    if not get_api_key():
        console.print(
            "[yellow]No API key configured. Run [bold]gitsmart configure[/bold] first.[/yellow]"
        )
        sys.exit(1)

    if lang is not None and not is_valid_language(lang):
        console.print(f"[red]✗ '{lang}' is not a valid ISO 639-1 language code.[/red]")
        sys.exit(1)

    language = lang.lower() if lang else get_commit_language()

    try:
        repo = Repo(search_parent_directories=True)
    except InvalidGitRepositoryError:
        console.print("[red]✗ Not inside a git repository.[/red]")
        sys.exit(1)

    if smart:
        _commit_smart(repo, language, length)
        return

    diff = repo.git.diff("--staged")
    if not diff:
        console.print("[yellow]No staged changes. Use [bold]git add[/bold] first.[/yellow]")
        sys.exit(1)

    if len(diff) > DIFF_MAX_CHARS:
        console.print(
            f"[yellow]⚠ Diff is large ({len(diff):,} chars), truncating to {DIFF_MAX_CHARS:,}.[/yellow]"
        )
        diff = diff[:DIFF_MAX_CHARS]

    client = GitSmartClient()
    try:
        with console.status("[cyan]Analyzing changes...[/cyan]"):
            result = client.post(
                "/v1/git/commit",
                {"diff": diff, "commit_type": commit_type, "language": language, "length": length},
                timeout=TIMEOUT_COMMIT,
            )
    except GitSmartAPIError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    message = result["message"]
    body = result.get("body")
    full_commit = message + (f"\n\n{body}" if body else "")

    display = f"[bold yellow]{message}[/bold yellow]"
    if body:
        display += f"\n\n[yellow]{body}[/yellow]"

    console.print()
    console.print(Panel(display, title="[bold]Suggested Commit[/bold]", border_style="green", box=box.HORIZONTALS))
    _show_file_status(repo)

    if auto:
        _do_commit(repo, full_commit)
        console.print(f"[green]✓[/green] Committed: [yellow]{message}[/yellow]\n")
        return

    answer = click.prompt("  Commit? [Y/n/e]", default="y", show_default=False)
    answer = answer.strip().lower()

    if answer in ("y", ""):
        _do_commit(repo, full_commit)
        console.print(f"[green]✓[/green] Committed: [yellow]{message}[/yellow]\n")
    elif answer == "e":
        edited = click.edit(full_commit)
        if edited and edited.strip():
            _do_commit(repo, edited.strip())
            console.print("[green]✓[/green] Committed.\n")
        else:
            console.print("[yellow]Aborted.[/yellow]\n")
    else:
        console.print("[yellow]Aborted.[/yellow]\n")


_STATUS_ICON = {
    "A": "[green]+[/green]",
    "M": "[yellow]~[/yellow]",
    "D": "[red]-[/red]",
    "R": "[cyan]→[/cyan]",
    "?": "[white]?[/white]",
}


def _parse_name_status(raw):
    """Parse git diff --name-status output into list of (status, path)."""
    result = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 2)
        status = parts[0][0]  # first char: A, M, D, R, etc.
        path = parts[-1]      # last part is always the target path
        result.append((status, path))
    return result


def _show_file_status(repo):
    staged_raw = repo.git.diff("--staged", "--name-status")
    unstaged_raw = repo.git.diff("--name-status")
    untracked = repo.untracked_files

    staged = _parse_name_status(staged_raw)
    unstaged = _parse_name_status(unstaged_raw)

    console.print(f"[bold white]Changes to be committed:[/bold white]")
    for status, path in staged:
        icon = _STATUS_ICON.get(status, " ")
        console.print(f"  {icon} [white]{path}[/white]")

    if unstaged or untracked:
        console.print(f"\n[bold white]Not staged:[/bold white]")
        for status, path in unstaged:
            icon = _STATUS_ICON.get(status, " ")
            console.print(f"  {icon} [white dim]{path}[/white dim]")
        for path in untracked:
            console.print(f"  {_STATUS_ICON['?']} [white dim]{path}[/white dim]")

    console.print()


def _do_commit(repo, message):
    try:
        repo.git.commit("-m", message)
    except GitCommandError as e:
        console.print(f"[red]✗ Git commit failed: {e}[/red]")
        sys.exit(1)


def _get_file_type(path):
    """Detect file type from extension."""
    ext = Path(path).suffix.lower()
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".tsx": "typescript", ".jsx": "javascript", ".java": "java",
        ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
        ".c": "c", ".cpp": "cpp", ".h": "header", ".hpp": "header",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".md": "markdown", ".txt": "text", ".sql": "sql",
        ".sh": "shell", ".bash": "shell",
    }
    return ext_map.get(ext, "unknown")


def _commit_smart(repo, language, length):
    """Smart commit mode - analyze and group staged files."""
    # Experimental feature warning
    console.print()
    console.print("[bold yellow]⚠  Smart Commit is an experimental feature[/bold yellow]")
    console.print("[white dim]AI will analyze your staged files and suggest logical commit groups.[/white dim]")
    console.print()

    if not click.confirm("  Continue?", default=True):
        console.print("[yellow]Aborted.[/yellow]\n")
        sys.exit(0)

    # Get staged files with diffs
    staged_raw = repo.git.diff("--staged", "--name-status")
    if not staged_raw:
        console.print("[yellow]No staged changes. Use [bold]git add[/bold] first.[/yellow]")
        sys.exit(1)

    staged_files = _parse_name_status(staged_raw)

    if len(staged_files) > SMART_MAX_FILES:
        console.print(
            f"[yellow]⚠ Too many staged files ({len(staged_files)}), "
            f"limit is {SMART_MAX_FILES}. Use regular commit instead.[/yellow]"
        )
        sys.exit(1)

    # Collect file changes with diffs
    file_changes = []
    for status, path in staged_files:
        try:
            diff = repo.git.diff("--staged", path)
            numstat = repo.git.diff("--staged", "--numstat", path)

            # Parse numstat: "additions\tdeletions\tfilename"
            parts = numstat.split("\t")
            additions = int(parts[0]) if parts[0] != "-" else 0
            deletions = int(parts[1]) if parts[1] != "-" else 0

            file_changes.append({
                "path": path,
                "diff": diff,
                "additions": additions,
                "deletions": deletions,
                "file_type": _get_file_type(path),
            })
        except Exception as e:
            console.print(f"[red]✗ Failed to get diff for {path}: {e}[/red]")
            sys.exit(1)

    # Call commit/smart API
    client = GitSmartClient()
    try:
        with console.status("[cyan]Analyzing files and grouping into commits...[/cyan]"):
            result = client.post(
                "/v1/git/commit/smart",
                {"files": file_changes, "language": language, "length": length},
                timeout=TIMEOUT_COMMIT_SMART,
            )
    except GitSmartAPIError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    groups = result["groups"]
    total_groups = result["total_groups"]

    if total_groups == 0:
        console.print("[yellow]No commit groups generated.[/yellow]")
        sys.exit(0)

    # If only 1 group - treat as normal commit
    if total_groups == 1:
        group = groups[0]
        message = group["message"]

        display = f"[bold yellow]{message.splitlines()[0]}[/bold yellow]"
        if len(message.splitlines()) > 1:
            body = "\n".join(message.splitlines()[1:]).strip()
            display += f"\n\n[yellow]{body}[/yellow]"

        console.print()
        console.print(Panel(display, title="[bold]Suggested Commit[/bold]", border_style="green", box=box.HORIZONTALS))
        console.print(f"[white dim]AI grouped all files into one commit.[/white dim]\n")
        _show_file_status(repo)

        answer = click.prompt("  Commit? [Y/n/e]", default="y", show_default=False)
        answer = answer.strip().lower()

        if answer in ("y", ""):
            _do_commit(repo, message)
            console.print(f"[green]✓[/green] Committed: [yellow]{message.splitlines()[0]}[/yellow]\n")
        elif answer == "e":
            edited = click.edit(message)
            if edited and edited.strip():
                _do_commit(repo, edited.strip())
                console.print("[green]✓[/green] Committed.\n")
            else:
                console.print("[yellow]Aborted.[/yellow]\n")
        else:
            console.print("[yellow]Aborted.[/yellow]\n")
        return

    # Multiple groups - show interactive selection
    console.print()
    console.print(f"[bold cyan]🤖 AI grouped {len(file_changes)} files into {total_groups} commits:[/bold cyan]\n")

    for i, group in enumerate(groups, 1):
        confidence_color = "green" if group["confidence"] >= 0.8 else "yellow" if group["confidence"] >= 0.6 else "red"

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="white")

        # Header
        table.add_row(f"[bold white]Group {i}:[/bold white] [{confidence_color}]{group['title']}[/{confidence_color}]")
        table.add_row(f"[white dim]Confidence: [{confidence_color}]{group['confidence']:.0%}[/{confidence_color}][/white dim]")
        table.add_row("")

        # Files
        for file in group["files"]:
            table.add_row(f"  [cyan]•[/cyan] [white]{file}[/white]")

        table.add_row("")
        table.add_row(f"[white dim]Reasoning: {group['reasoning']}[/white dim]")

        console.print(table)
        console.print()

    # Interactive selection
    console.print("[bold white]Options:[/bold white]")
    console.print("  [green]a[/green] - Commit all groups")
    console.print("  [yellow]s[/yellow] - Select specific groups (e.g., 1,3,4)")
    console.print("  [red]c[/red] - Cancel")
    console.print()

    answer = click.prompt("  Choose", default="a", show_default=False)
    answer = answer.strip().lower()

    if answer == "c":
        console.print("[yellow]Aborted.[/yellow]\n")
        return

    selected_indices = []
    if answer == "a":
        selected_indices = list(range(len(groups)))
    elif answer == "s":
        selection = click.prompt("  Enter group numbers (e.g., 1,3,4)", type=str)
        try:
            selected_indices = [int(x.strip()) - 1 for x in selection.split(",")]
            # Validate
            for idx in selected_indices:
                if idx < 0 or idx >= len(groups):
                    console.print(f"[red]✗ Invalid group number: {idx + 1}[/red]")
                    sys.exit(1)
        except ValueError:
            console.print("[red]✗ Invalid selection format.[/red]")
            sys.exit(1)
    else:
        console.print("[yellow]Aborted.[/yellow]\n")
        return

    if not selected_indices:
        console.print("[yellow]No groups selected.[/yellow]\n")
        return

    # Commit selected groups
    console.print()
    committed = []
    failed = []

    for idx in selected_indices:
        group = groups[idx]
        message = group["message"]
        files = group["files"]

        # Unstage all files first, then stage only this group's files
        try:
            repo.git.reset("HEAD", "--", ".")
            for file in files:
                repo.git.add(file)

            _do_commit(repo, message)
            committed.append(group)
            console.print(f"[green]✓[/green] Group {idx + 1}: [yellow]{group['title']}[/yellow]")

        except GitCommandError as e:
            failed.append((group, str(e)))
            console.print(f"[red]✗[/red] Group {idx + 1} failed: {e}")

            # Re-stage remaining files
            console.print("[yellow]Re-staging remaining files...[/yellow]")
            for file_change in file_changes:
                try:
                    repo.git.add(file_change["path"])
                except:
                    pass
            break

    # Summary
    console.print()
    if committed:
        console.print(f"[bold green]✓ Successfully committed {len(committed)} group(s).[/bold green]")

    if failed:
        console.print(f"[bold red]✗ {len(failed)} group(s) failed.[/bold red]")
        console.print("[yellow]Remaining files have been re-staged.[/yellow]")

    console.print()
