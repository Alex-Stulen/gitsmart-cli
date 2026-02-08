import sys

import click
from rich.console import Console
from rich.table import Table

from gitsmart.client import GitSmartAPIError, GitSmartClient
from gitsmart.config import get_api_key

console = Console()


def _usage_bar(used, limit, width=20):
    filled = int(width * used / limit) if limit > 0 else 0
    return "[green]" + "█" * filled + "[/green][dim]" + "░" * (width - filled) + "[/dim]"


@click.command()
def usage():
    """Show API usage for the current month."""
    if not get_api_key():
        console.print(
            "[yellow]No API key configured. Run [bold]gitsmart configure[/bold] first.[/yellow]"
        )
        sys.exit(1)

    client = GitSmartClient()
    try:
        usage = client.get("/v1/cli/users/me/usage")
    except GitSmartAPIError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    used = usage["requests_used"]
    limit = usage["requests_limit"]
    remaining = usage["requests_remaining"]
    plan = usage["plan"].capitalize()
    month = usage["month"][:7]  # YYYY-MM

    remaining_color = "green" if remaining > 0 else "red"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Plan", f"[cyan]{plan}[/cyan]")
    table.add_row("Period", month)
    table.add_row("Used", f"{used:,} / {limit:,}")
    table.add_row("Remaining", f"[{remaining_color}]{remaining:,}[/{remaining_color}]")
    table.add_row("", _usage_bar(used, limit))

    console.print()
    console.print(f"[bold]API Usage — {month}[/bold]")
    console.print(table)
    console.print()
