"""Smart commit functionality."""
import sys
from pathlib import Path

import click
from git import GitCommandError
from rich.console import Console
from rich.table import Table

from gitsmart.client import GitSmartClient
from gitsmart.config import TIMEOUT_COMMIT_SMART
from gitsmart.utils.api import call_api
from gitsmart.utils.credits import display_operation_cost
from gitsmart.utils.display import show_file_status
from gitsmart.utils.git import parse_name_status
from gitsmart.utils.prompts import confirm_commit, do_commit

console = Console()

SMART_MAX_FILES = 50


def get_file_type(path):
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


def collect_file_changes(repo, staged_files):
    """Collect file changes with diffs and stats."""
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
                "file_type": get_file_type(path),
            })
        except Exception as e:
            console.print(f"[red]✗ Failed to get diff for {path}: {e}[/red]")
            sys.exit(1)
    return file_changes


def handle_single_group(repo, group):
    """Handle commit when AI grouped all files into one commit."""
    message = group["message"]
    first_line, body = _split_message(message)

    from gitsmart.utils.display import show_commit_message
    show_commit_message(first_line, body)
    console.print(f"[white dim]AI grouped all files into one commit.[/white dim]\n")
    show_file_status(repo)

    confirm_commit(repo, message, first_line)


def handle_multiple_groups(repo, groups, file_changes):
    """Handle commit when AI grouped files into multiple commits."""
    console.print()
    console.print(f"[bold cyan]🤖 AI grouped {len(file_changes)} files into {len(groups)} commits:[/bold cyan]\n")

    display_groups(groups)
    selected_indices = prompt_group_selection(groups)

    if not selected_indices:
        console.print("[yellow]No groups selected.[/yellow]\n")
        return

    commit_selected_groups(repo, groups, selected_indices, file_changes)


def display_groups(groups):
    """Display commit groups in a table."""
    for i, group in enumerate(groups, 1):
        confidence_color = _get_confidence_color(group["confidence"])

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="white")

        table.add_row(f"[bold white]Group {i}:[/bold white] [{confidence_color}]{group['title']}[/{confidence_color}]")
        table.add_row(f"[white dim]Confidence: [{confidence_color}]{group['confidence']:.0%}[/{confidence_color}][/white dim]")
        table.add_row("")

        for file in group["files"]:
            table.add_row(f"  [cyan]•[/cyan] [white]{file}[/white]")

        table.add_row("")
        table.add_row(f"[white dim]Reasoning: {group['reasoning']}[/white dim]")

        console.print(table)
        console.print()


def prompt_group_selection(groups):
    """Prompt user to select which groups to commit."""
    console.print("[bold white]Options:[/bold white]")
    console.print("  [green]a[/green] - Commit all groups")
    console.print("  [yellow]s[/yellow] - Select specific groups (e.g., 1,3,4)")
    console.print("  [red]c[/red] - Cancel")
    console.print()

    answer = click.prompt("  Choose", default="a", show_default=False)
    answer = answer.strip().lower()

    if answer == "c":
        console.print("[yellow]Aborted.[/yellow]\n")
        return []

    if answer == "a":
        return list(range(len(groups)))

    if answer == "s":
        selection = click.prompt("  Enter group numbers (e.g., 1,3,4)", type=str)
        return _parse_selection(selection, len(groups))

    console.print("[yellow]Aborted.[/yellow]\n")
    return []


def commit_selected_groups(repo, groups, selected_indices, file_changes):
    """Commit the selected groups."""
    console.print()
    committed = []
    failed = []

    for idx in selected_indices:
        group = groups[idx]
        success = _commit_group(repo, group, idx)

        if success:
            committed.append(group)
        else:
            failed.append(group)
            _restage_files(repo, file_changes)
            break

    _print_summary(committed, failed)


def _split_message(message):
    """Split commit message into first line and body."""
    lines = message.splitlines()
    if not lines:
        return "", None
    first_line = lines[0]
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else None
    return first_line, body


def _get_confidence_color(confidence):
    """Get color based on confidence level."""
    if confidence >= 0.8:
        return "green"
    elif confidence >= 0.6:
        return "yellow"
    else:
        return "red"


def _parse_selection(selection, max_groups):
    """Parse user selection string into list of indices."""
    try:
        indices = [int(x.strip()) - 1 for x in selection.split(",")]
        for idx in indices:
            if idx < 0 or idx >= max_groups:
                console.print(f"[red]✗ Invalid group number: {idx + 1}[/red]")
                sys.exit(1)
        return indices
    except ValueError:
        console.print("[red]✗ Invalid selection format.[/red]")
        sys.exit(1)


def _commit_group(repo, group, idx):
    """Commit a single group. Returns True on success, False on failure."""
    message = group["message"]
    files = group["files"]

    try:
        # Unstage all files first, then stage only this group's files
        repo.git.reset("HEAD", "--", ".")
        for file in files:
            repo.git.add(file)

        do_commit(repo, message)
        console.print(f"[green]✓[/green] Group {idx + 1}: [yellow]{group['title']}[/yellow]")
        return True
    except GitCommandError as e:
        console.print(f"[red]✗[/red] Group {idx + 1} failed: {e}")
        return False


def _restage_files(repo, file_changes):
    """Re-stage files after a failed commit."""
    console.print("[yellow]Re-staging remaining files...[/yellow]")
    for file_change in file_changes:
        try:
            repo.git.add(file_change["path"])
        except:
            pass


def _print_summary(committed, failed):
    """Print summary of commit results."""
    console.print()
    if committed:
        console.print(f"[bold green]✓ Successfully committed {len(committed)} group(s).[/bold green]")

    if failed:
        console.print(f"[bold red]✗ {len(failed)} group(s) failed.[/bold red]")
        console.print("[yellow]Remaining files have been re-staged.[/yellow]")

    console.print()


def execute_smart_commit(repo, language, length, hint=None, usage_before=None):
    """Execute smart commit workflow."""
    # Experimental feature warning
    console.print()
    console.print("[bold yellow]⚠  Smart Commit is an experimental feature[/bold yellow]")
    console.print("[white dim]AI will analyze your staged files and suggest logical commit groups.[/white dim]")
    console.print()

    if not click.confirm("  Continue?", default=True):
        console.print("[yellow]Aborted.[/yellow]\n")
        sys.exit(0)

    # Get and validate staged files
    staged_raw = repo.git.diff("--staged", "--name-status")
    if not staged_raw:
        console.print("[yellow]No staged changes. Use [bold]git add[/bold] first.[/yellow]")
        sys.exit(1)

    staged_files = parse_name_status(staged_raw)
    if len(staged_files) > SMART_MAX_FILES:
        console.print(
            f"[yellow]⚠ Too many staged files ({len(staged_files)}), "
            f"limit is {SMART_MAX_FILES}. Use regular commit instead.[/yellow]"
        )
        sys.exit(1)

    # Collect file changes
    file_changes = collect_file_changes(repo, staged_files)

    # Call API
    client = GitSmartClient()
    payload = {"files": file_changes, "language": language, "length": length}
    if hint:
        payload["ai_hint"] = hint

    result = call_api(
        client,
        "post",
        "/v1/git/commit/smart",
        payload,
        timeout=TIMEOUT_COMMIT_SMART,
        status_message="Analyzing files and grouping into commits..."
    )

    groups = result["groups"]
    total_groups = result["total_groups"]

    if total_groups == 0:
        console.print("[yellow]No commit groups generated.[/yellow]")
        sys.exit(0)

    # Display operation cost
    if usage_before:
        console.print()
        display_operation_cost(usage_before)
        console.print()

    # Handle results
    if total_groups == 1:
        handle_single_group(repo, groups[0])
    else:
        handle_multiple_groups(repo, groups, file_changes)
