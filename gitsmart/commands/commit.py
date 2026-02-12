"""Commit command."""
import sys

import click
from rich.console import Console

from gitsmart.client import GitSmartClient
from gitsmart.config import TIMEOUT_COMMIT, HINT_MAX_LENGTH
from gitsmart.utils.api import call_api
from gitsmart.utils.credits import check_credits_before_operation, display_operation_cost
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
@click.option("--detail", "-d", "length", flag_value="detail", help="Generate detailed commit message with full body.")
@click.option(
    "--hint", "-p", "--prompt",
    default=None,
    metavar="TEXT",
    help=f"Additional context for AI (max {HINT_MAX_LENGTH} chars).",
)
@validate_language
@require_git_repo
@require_api_key
def commit(auto, smart, commit_type, lang, length, hint, repo, language):
    """Generate AI commit message from staged changes."""
    # Validate hint length
    if hint and len(hint) > HINT_MAX_LENGTH:
        console.print(f"[red]✗ Hint must be {HINT_MAX_LENGTH} characters or less.[/red]")
        sys.exit(1)

    # Check credits before operation
    usage_before = check_credits_before_operation("commit generation")

    # Handle smart commit mode
    if smart:
        execute_smart_commit(repo, language, length, hint, usage_before)
        return

    # Get staged diff
    diff, truncated = get_staged_diff(repo, DIFF_MAX_CHARS)
    if not diff:
        console.print("[yellow]No staged changes. Use [yellow]git add[/yellow] first.[/yellow]")
        sys.exit(1)

    if truncated:
        console.print(
            f"[yellow]⚠ Diff is large (>{DIFF_MAX_CHARS:,} chars), truncated.[/yellow]"
        )

    # Call API
    client = GitSmartClient()
    payload = {"diff": diff, "commit_type": commit_type, "language": language, "length": length}
    if hint:
        payload["ai_hint"] = hint

    result = call_api(
        client,
        "post",
        "/v1/git/commit",
        payload,
        timeout=TIMEOUT_COMMIT,
        status_message="Analyzing changes..."
    )

    message = result["message"]
    body = result.get("body")
    full_commit = message + (f"\n\n{body}" if body else "")

    # Display
    show_commit_message(message, body)
    show_file_status(repo)
    console.print()
    display_operation_cost(usage_before)

    # Auto commit or prompt
    if auto:
        do_commit(repo, full_commit)
        console.print(f"[green]✓[/green] Committed: [yellow]{message}[/yellow]\n")
    else:
        confirm_commit(repo, full_commit, message)
