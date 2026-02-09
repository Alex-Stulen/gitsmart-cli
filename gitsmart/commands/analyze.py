"""Analyze command."""
import sys
from datetime import datetime, timedelta

import click
from rich.console import Console

from gitsmart.client import GitSmartClient
from gitsmart.config import TIMEOUT_ANALYZE, HINT_MAX_LENGTH
from gitsmart.utils.analyze import (
    build_analysis_payload,
    collect_git_stats,
    detect_languages,
    display_analysis,
)
from gitsmart.utils.api import call_api
from gitsmart.utils.credits import check_credits_before_operation, display_operation_cost
from gitsmart.utils.decorators import require_api_key, require_git_repo, validate_language

console = Console()

SINCE_DAYS = 90  # last 3 months


@click.command()
@click.option("--lang", default=None, metavar="LANG", help="Analysis language (ISO 639-1), overrides config.")
@click.option(
    "--hint", "-p", "--prompt",
    default=None,
    metavar="TEXT",
    help=f"Additional context for AI (max {HINT_MAX_LENGTH} chars).",
)
@validate_language
@require_git_repo
@require_api_key
def analyze(lang, hint, repo, language):
    """Analyze repository statistics and get AI insights."""
    # Validate hint length
    if hint and len(hint) > HINT_MAX_LENGTH:
        console.print(f"[red]✗ Hint must be {HINT_MAX_LENGTH} characters or less.[/red]")
        sys.exit(1)

    since_date = (datetime.now() - timedelta(days=SINCE_DAYS)).strftime("%Y-%m-%d")

    # Check credits before operation
    usage_before = check_credits_before_operation("repository analysis")

    with console.status("[cyan]Collecting repository stats...[/cyan]"):
        commits, total_files = collect_git_stats(repo, since_date)
        languages = detect_languages(repo)

    if not commits:
        console.print("[yellow]No commits found in the last 3 months.[/yellow]")
        sys.exit(0)

    payload = build_analysis_payload(commits, total_files, languages, language)
    if hint:
        payload["ai_hint"] = hint

    client = GitSmartClient()
    result = call_api(
        client,
        "post",
        "/v1/git/analyze",
        payload,
        timeout=TIMEOUT_ANALYZE,
        status_message="Analyzing..."
    )

    display_analysis(result, payload)
    display_operation_cost(usage_before)
