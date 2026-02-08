"""Analyze command."""
import sys
from datetime import datetime, timedelta

import click
from rich.console import Console

from gitsmart.client import GitSmartClient
from gitsmart.config import TIMEOUT_ANALYZE
from gitsmart.utils.analyze import (
    build_analysis_payload,
    collect_git_stats,
    detect_languages,
    display_analysis,
)
from gitsmart.utils.api import call_api
from gitsmart.utils.decorators import require_api_key, require_git_repo, validate_language

console = Console()

SINCE_DAYS = 90  # last 3 months


@click.command()
@click.option("--lang", default=None, metavar="LANG", help="Analysis language (ISO 639-1), overrides config.")
@validate_language
@require_git_repo
@require_api_key
def analyze(lang, repo, language):
    """Analyze repository statistics and get AI insights."""
    since_date = (datetime.now() - timedelta(days=SINCE_DAYS)).strftime("%Y-%m-%d")

    with console.status("[cyan]Collecting repository stats...[/cyan]"):
        commits, total_files = collect_git_stats(repo, since_date)
        languages = detect_languages(repo)

    if not commits:
        console.print("[yellow]No commits found in the last 3 months.[/yellow]")
        sys.exit(0)

    payload = build_analysis_payload(commits, total_files, languages, language)

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
