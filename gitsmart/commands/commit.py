"""Commit command."""
import sys

import click
from rich.console import Console

from gitsmart.client import GitSmartClient
from gitsmart.config import TIMEOUT_COMMIT
from gitsmart.utils.api import call_api
from gitsmart.utils.decorators import require_api_key, require_git_repo, validate_language
from gitsmart.utils.display import show_commit_message, show_file_status
from gitsmart.utils.git import get_staged_diff
from gitsmart.utils.prompts import confirm_commit, do_commit
from gitsmart.utils.smart_commit import execute_smart_commit

console = Console()

DIFF_MAX_CHARS = 100_000


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
@require_api_key
@require_git_repo
@validate_language
def commit(auto, smart, commit_type, lang, length, repo, language):
    """Generate AI commit message from staged changes."""
    # Handle smart commit mode
    if smart:
        execute_smart_commit(repo, language, length)
        return

    # Get staged diff
    diff, truncated = get_staged_diff(repo, DIFF_MAX_CHARS)
    if not diff:
        console.print("[yellow]No staged changes. Use [bold]git add[/bold] first.[/yellow]")
        sys.exit(1)

    if truncated:
        console.print(
            f"[yellow]⚠ Diff is large (>{DIFF_MAX_CHARS:,} chars), truncated.[/yellow]"
        )

    # Call API
    client = GitSmartClient()
    result = call_api(
        client,
        "post",
        "/v1/git/commit",
        {"diff": diff, "commit_type": commit_type, "language": language, "length": length},
        timeout=TIMEOUT_COMMIT,
        status_message="Analyzing changes..."
    )

    message = result["message"]
    body = result.get("body")
    full_commit = message + (f"\n\n{body}" if body else "")

    # Display
    show_commit_message(message, body)
    show_file_status(repo)

    # Auto commit or prompt
    if auto:
        do_commit(repo, full_commit)
        console.print(f"[green]✓[/green] Committed: [yellow]{message}[/yellow]\n")
    else:
        confirm_commit(repo, full_commit, message)
