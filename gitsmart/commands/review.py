import re
import sys

import click
from git import InvalidGitRepositoryError, Repo
from rich.console import Console

from gitsmart.client import GitSmartAPIError, GitSmartClient
from gitsmart.config import get_api_key, get_commit_language, TIMEOUT_REVIEW
from gitsmart.lang import is_valid_language

console = Console()

DIFF_MAX_CHARS = 100_000

_SEVERITY_STYLE = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "white dim",
}

_COMPLEXITY_STYLE = {
    "low": "green",
    "medium": "yellow",
    "high": "red",
}


def _detect_base_branch(repo):
    branches = {b.name for b in repo.branches}
    if "main" in branches:
        return "main"
    if "master" in branches:
        return "master"
    return None


def _parse_shortstat(shortstat):
    """Parse git diff --shortstat output into (files, added, removed)."""
    files = added = removed = None
    m = re.search(r"(\d+) files? changed", shortstat)
    if m:
        files = int(m.group(1))
    m = re.search(r"(\d+) insertion", shortstat)
    if m:
        added = int(m.group(1))
    m = re.search(r"(\d+) deletion", shortstat)
    if m:
        removed = int(m.group(1))
    return files, added, removed


@click.command()
@click.option("--branch", default=None, metavar="BRANCH", help="Branch to review (default: current).")
@click.option("--base", default=None, metavar="BRANCH", help="Base branch to compare against (default: main or master).")
@click.option("--lang", default=None, metavar="LANG", help="Review language (ISO 639-1), overrides config.")
def review(branch, base, lang):
    """Review changes between branches."""
    if not get_api_key():
        console.print(
            "[yellow]No API key configured. Run [bold yellow]gitsmart configure[/bold yellow] first.[/yellow]"
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

    try:
        current_branch = branch or repo.active_branch.name
    except TypeError:
        console.print("[red]✗ Detached HEAD state. Use [bold red]--branch[/bold red] to specify the branch.[/red]")
        sys.exit(1)

    if base is None:
        base = _detect_base_branch(repo)
        if base is None:
            console.print(
                "[red]✗ Could not detect base branch. Use [bold red]--base[/bold red] to specify.[/red]"
            )
            sys.exit(1)

    branches = {b.name for b in repo.branches}
    if current_branch not in branches:
        console.print(f"[red]✗ Branch '{current_branch}' not found.[/red]")
        sys.exit(1)
    if base not in branches:
        console.print(f"[red]✗ Base branch '{base}' not found.[/red]")
        sys.exit(1)

    if current_branch == base:
        console.print(
            f"[yellow]Current branch is the same as base branch ({base}). Nothing to review.[/yellow]"
        )
        sys.exit(0)

    try:
        diff = repo.git.diff(f"{base}...{current_branch}")
        shortstat = repo.git.diff("--shortstat", f"{base}...{current_branch}")
    except Exception as e:
        console.print(f"[red]✗ Failed to get diff: {e}[/red]")
        sys.exit(1)

    if not diff:
        console.print(
            f"[yellow]No differences between [bold yellow]{current_branch}[/bold yellow]"
            f" and [bold yellow]{base}[/bold yellow].[/yellow]"
        )
        sys.exit(0)

    files_changed, lines_added, lines_removed = _parse_shortstat(shortstat)

    if len(diff) > DIFF_MAX_CHARS:
        console.print(
            f"[yellow]⚠ Diff is large ({len(diff):,} chars), truncating to {DIFF_MAX_CHARS:,}.[/yellow]"
        )
        diff = diff[:DIFF_MAX_CHARS]

    client = GitSmartClient()
    try:
        with console.status("[cyan]Analyzing changes...[/cyan]"):
            result = client.post(
                "/v1/git/review",
                {
                    "diff": diff,
                    "branch": current_branch,
                    "base_branch": base,
                    "files_changed": files_changed,
                    "lines_added": lines_added,
                    "lines_removed": lines_removed,
                    "language": language,
                },
                timeout=TIMEOUT_REVIEW,
            )
    except GitSmartAPIError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    _display_review(result, current_branch)


def _display_review(result, branch):
    separator = "[green]─────────────────────────────────────[/green]"
    complexity = result["complexity"]
    complexity_color = _COMPLEXITY_STYLE.get(complexity, "white")

    console.print()
    console.print(f"[bold cyan]📊 Review Summary for {branch}[/bold cyan]")
    console.print(separator)

    changes = result.get("changes")
    if changes:
        console.print(f"[white]📝 Changes: {changes} lines[/white]")

    what_changed = result.get("what_changed") or []
    if what_changed:
        console.print(f"\n[bold white]🎯 What's changed:[/bold white]")
        for item in what_changed:
            console.print(f"[white]- {item}[/white]")

    issues = result.get("issues") or []
    if issues:
        console.print(f"\n[bold white]⚠️  Potential issues:[/bold white]")
        for issue in issues:
            severity = issue["severity"]
            style = _SEVERITY_STYLE.get(severity, "white")
            location = issue.get("location")
            loc_str = f" ({location})" if location else ""
            console.print(f"[{style}]- {issue['description']}{loc_str}[/{style}]")

    recommendations = result.get("recommendations") or []
    if recommendations:
        console.print(f"\n[bold white]💡 Recommendations:[/bold white]")
        for rec in recommendations:
            console.print(f"[white]- {rec}[/white]")

    console.print(
        f"\n[bold white]🔢 Complexity:[/bold white]"
        f" [{complexity_color}]{complexity.capitalize()}[/{complexity_color}]"
    )
    console.print()
