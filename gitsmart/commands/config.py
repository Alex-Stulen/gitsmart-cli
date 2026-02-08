import sys

import click
from rich.console import Console
from rich.table import Table

from gitsmart.config import KNOWN_KEYS, load_config, save_config
from gitsmart.lang import is_valid_language

console = Console()

_VALIDATORS = {
    "api_key": lambda v: (len(v) > 0, "API key cannot be empty."),
    "api_url": lambda v: (
        v.startswith("http://") or v.startswith("https://"),
        "API URL must start with http:// or https://",
    ),
    "commit_language": lambda v: (
        is_valid_language(v),
        f"'{v}' is not a valid ISO 639-1 language code.",
    ),
}


def _mask(key, value):
    if key == "api_key" and value and len(value) > 10:
        return value[:8] + "***" + value[-4:]
    return value


@click.command(name="config")
@click.argument("key", required=False)
@click.argument("value", required=False)
def config_cmd(key, value):
    """Read or write configuration values.

    \b
    Examples:
      gitsmart config                        show all settings
      gitsmart config commit_language        show current value
      gitsmart config commit_language ru     set to Russian
    """
    current = load_config()

    if key is None:
        if not current:
            console.print("[yellow]No configuration found. Run [bold]gitsmart configure[/bold] first.[/yellow]")
            return
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="dim")
        table.add_column()
        for k in KNOWN_KEYS:
            v = current.get(k, "")
            table.add_row(k, _mask(k, v) if v else "[dim](not set)[/dim]")
        console.print()
        console.print("[bold]GitSmart Configuration[/bold]")
        console.print(table)
        console.print()
        return

    if key not in KNOWN_KEYS:
        console.print(
            f"[red]✗ Unknown key '{key}'. Allowed: {', '.join(KNOWN_KEYS)}[/red]"
        )
        sys.exit(1)

    if value is None:
        v = current.get(key, "")
        console.print(_mask(key, v) if v else "[dim](not set)[/dim]")
        return

    ok, error_msg = _VALIDATORS[key](value)
    if not ok:
        console.print(f"[red]✗ {error_msg}[/red]")
        sys.exit(1)

    current[key] = value.lower() if key == "commit_language" else value
    save_config(current)
    console.print(f"[green]✓[/green] {key} = {_mask(key, current[key])}")
