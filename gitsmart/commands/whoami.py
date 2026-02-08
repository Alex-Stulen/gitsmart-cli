"""Whoami command."""
from rich.console import Console
from rich.table import Table

import click
from gitsmart.client import GitSmartClient
from gitsmart.utils.api import call_api
from gitsmart.utils.decorators import require_api_key

console = Console()


@click.command()
@require_api_key
def whoami():
    """Show current account information."""
    client = GitSmartClient()
    user = call_api(client, "get", "/v1/cli/users/me")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Email", f"[green]{user['email']}[/green]")
    table.add_row("Plan", f"[cyan]{user['plan'].capitalize()}[/cyan]")

    console.print()
    console.print("[yellow]GitSmart Account[/yellow]")
    console.print(table)
    console.print()
