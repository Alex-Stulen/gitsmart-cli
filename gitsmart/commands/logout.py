import sys

import click
from rich.console import Console

from gitsmart.config import CONFIG_FILE

console = Console()


@click.command()
def logout():
    """Remove saved API key and configuration."""
    if not CONFIG_FILE.exists():
        console.print("[yellow]Not configured. Nothing to remove.[/yellow]")
        return

    console.print(f"\n[yellow]This will delete[/yellow] [yellow]{CONFIG_FILE}[/yellow]\n")
    if not click.confirm("  Are you sure?", default=False):
        console.print("[yellow]Aborted.[/yellow]\n")
        return

    CONFIG_FILE.unlink()
    console.print("[green]✓[/green] Logged out. Configuration removed.\n")
