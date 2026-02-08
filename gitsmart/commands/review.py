"""Review command."""
import sys

import click
from rich.console import Console

from gitsmart.client import GitSmartClient
from gitsmart.config import TIMEOUT_REVIEW
from gitsmart.utils.api import call_api
from gitsmart.utils.decorators import require_api_key, require_git_repo, validate_language
from gitsmart.utils.git import detect_base_branch, parse_shortstat

console = Console()

DIFF_MAX_CHARS = 100_000

SEVERITY_STYLE = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "white dim",
}

COMPLEXITY_STYLE = {
    "low": "green",
    "medium": "yellow",
    "high": "red",
}


def get_current_branch(repo, branch):
    """Get current branch name, handling detached HEAD."""
    if branch:
        return branch
    try:
        return repo.active_branch.name
    except TypeError:
        console.print("[red]✗ Detached HEAD state. Use [bold red]--branch[/bold red] to specify the branch.[/red]")
        sys.exit(1)


def validate_branches(repo, current_branch, base):
    """Validate that branches exist and are different."""
    branches = {b.name for b in repo.branches}

    if current_branch not in branches:
        console.print(f"[red]✗ Branch '{current_branch}' not found.[/red]")
        sys.exit(1)

    if base not in branches:
        console.print(f"[red]✗ Base branch '{base}' not found.[/red]")
        sys.exit(1)

    if current_branch == base:
        console.print(f"[yellow]Current branch is the same as base branch ({base}). Nothing to review.[/yellow]")
        sys.exit(0)


def get_diff_stats(repo, base, current_branch):
    """Get diff and statistics between branches."""
    try:
        diff = repo.git.diff(f"{base}...{current_branch}")
        shortstat = repo.git.diff("--shortstat", f"{base}...{current_branch}")
        return diff, shortstat
    except Exception as e:
        console.print(f"[red]✗ Failed to get diff: {e}[/red]")
        sys.exit(1)


def display_review(result, branch):
    """Display review results."""
    separator = "[green]─────────────────────────────────────[/green]"
    complexity = result["complexity"]
    complexity_color = COMPLEXITY_STYLE.get(complexity, "white")

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
            style = SEVERITY_STYLE.get(severity, "white")
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


@click.command()
@click.option("--branch", default=None, metavar="BRANCH", help="Branch to review (default: current).")
@click.option("--base", default=None, metavar="BRANCH", help="Base branch to compare against (default: main or master).")
@click.option("--lang", default=None, metavar="LANG", help="Review language (ISO 639-1), overrides config.")
@validate_language
@require_git_repo
@require_api_key
def review(branch, base, lang, repo, language):
    """Review changes between branches."""
    current_branch = get_current_branch(repo, branch)

    if base is None:
        base = detect_base_branch(repo)
        if base is None:
            console.print("[red]✗ Could not detect base branch. Use [bold red]--base[/bold red] to specify.[/red]")
            sys.exit(1)

    validate_branches(repo, current_branch, base)

    diff, shortstat = get_diff_stats(repo, base, current_branch)

    if not diff:
        console.print(
            f"[yellow]No differences between [bold yellow]{current_branch}[/bold yellow]"
            f" and [bold yellow]{base}[/bold yellow].[/yellow]"
        )
        sys.exit(0)

    files_changed, lines_added, lines_removed = parse_shortstat(shortstat)

    if len(diff) > DIFF_MAX_CHARS:
        console.print(f"[yellow]⚠ Diff is large ({len(diff):,} chars), truncating to {DIFF_MAX_CHARS:,}.[/yellow]")
        diff = diff[:DIFF_MAX_CHARS]

    client = GitSmartClient()
    result = call_api(
        client,
        "post",
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
        status_message="Analyzing changes..."
    )

    display_review(result, current_branch)
