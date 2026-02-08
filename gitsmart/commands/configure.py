import sys

import click
from rich.console import Console

from gitsmart.client import GitSmartAPIError, GitSmartClient
from gitsmart.config import CONFIG_FILE, DEFAULT_API_URL, DEFAULT_COMMIT_LANGUAGE, load_config, save_config
from gitsmart.lang import is_valid_language, language_name

console = Console()


@click.command()
def configure():
    """Configure GitSmart with your API key."""
    current = load_config()

    console.print("\n[bold]GitSmart Configuration[/bold]\n")

    api_key = click.prompt("  Enter your API key", hide_input=True)
    api_url = click.prompt("  API URL", default=current.get("api_url") or DEFAULT_API_URL)

    lang = click.prompt(
        "  Commit language (ISO 639-1)",
        default=current.get("commit_language") or DEFAULT_COMMIT_LANGUAGE,
    )
    if not is_valid_language(lang):
        console.print(f"[red]✗ '{lang}' is not a valid ISO 639-1 language code.[/red]\n")
        sys.exit(1)

    console.print()
    try:
        with console.status("[cyan]Validating API key...[/cyan]"):
            client = GitSmartClient(api_key=api_key, api_url=api_url)
            user = client.get("/v1/cli/users/me")
    except GitSmartAPIError as e:
        console.print(f"[red]✗ {e}[/red]\n")
        sys.exit(1)

    current.update({"api_key": api_key, "api_url": api_url, "commit_language": lang.lower()})
    save_config(current)

    console.print(
        f"[green]✓[/green] Authenticated as [bold]{user['email']}[/bold]"
        f" ([cyan]{user['plan'].capitalize()}[/cyan] plan)"
    )
    console.print(
        f"[green]✓[/green] Commit language set to"
        f" [bold]{language_name(lang)}[/bold] ([dim]{lang.lower()}[/dim])"
    )
    console.print(f"[green]✓[/green] Configuration saved to [dim]{CONFIG_FILE}[/dim]\n")
