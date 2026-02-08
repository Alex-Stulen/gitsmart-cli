"""Usage command."""
import click
from rich.console import Console
from rich.table import Table

from gitsmart.client import GitSmartClient
from gitsmart.utils.api import call_api
from gitsmart.utils.decorators import require_api_key

console = Console()


def usage_bar(used, limit, width=20):
    """Generate usage progress bar."""
    filled = int(width * used / limit) if limit > 0 else 0
    return "[green]" + "█" * filled + "[/green][dim]" + "░" * (width - filled) + "[/dim]"


@click.command()
@require_api_key
def usage():
    """Show API usage for the current month."""
    client = GitSmartClient()
    usage_data = call_api(client, "get", "/v1/cli/users/me/usage")

    used = usage_data["requests_used"]
    limit = usage_data["requests_limit"]
    remaining = usage_data["requests_remaining"]
    plan = usage_data["plan"].capitalize()
    month = usage_data["month"][:7]  # YYYY-MM

    remaining_color = "green" if remaining > 0 else "red"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Plan", f"[cyan]{plan}[/cyan]")
    table.add_row("Period", month)
    table.add_row("Used", f"{used:,} / {limit:,}")
    table.add_row("Remaining", f"[{remaining_color}]{remaining:,}[/{remaining_color}]")
    table.add_row("", usage_bar(used, limit))

    console.print()
    console.print(f"[yellow]API Usage — {month}[/yellow]")
    console.print(table)
    console.print()
