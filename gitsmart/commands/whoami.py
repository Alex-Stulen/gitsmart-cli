import sys

import click
from rich.console import Console
from rich.table import Table

from gitsmart.client import GitSmartAPIError, GitSmartClient
from gitsmart.config import get_api_key

console = Console()


@click.command()
def whoami():
    """Show current account information."""
    if not get_api_key():
        console.print(
            "[yellow]No API key configured. Run [bold]gitsmart configure[/bold] first.[/yellow]"
        )
        sys.exit(1)

    client = GitSmartClient()
    try:
        user = client.get("/v1/cli/users/me")
    except GitSmartAPIError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Email", f"[bold]{user['email']}[/bold]")
    table.add_row("Plan", f"[cyan]{user['plan'].capitalize()}[/cyan]")

    console.print()
    console.print("[bold]GitSmart Account[/bold]")
    console.print(table)
    console.print()
