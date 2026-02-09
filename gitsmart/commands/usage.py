"""Usage command."""
import click
from rich.console import Console
from rich.table import Table

from gitsmart.client import GitSmartClient
from gitsmart.config import LOW_CREDITS_WARNING, CRITICAL_CREDITS_WARNING
from gitsmart.utils.api import call_api
from gitsmart.utils.decorators import require_api_key

console = Console()


def credits_bar(used, limit, is_overdraft, width=20):
    """Generate credits progress bar."""
    if is_overdraft or used > limit:
        # Show full red bar for overdraft
        return "[red]" + "█" * width + "[/red]"

    filled = int(width * used / limit) if limit > 0 else 0
    remaining_pct = (limit - used) / limit if limit > 0 else 0

    # Color based on remaining percentage
    if remaining_pct < 0.1:  # < 10%
        color = "red"
    elif remaining_pct < 0.2:  # < 20%
        color = "yellow"
    else:
        color = "green"

    return f"[{color}]" + "█" * filled + f"[/{color}][dim]" + "░" * (width - filled) + "[/dim]"


@click.command()
@require_api_key
def usage():
    """Show credits usage for the current month."""
    client = GitSmartClient()
    usage_data = call_api(client, "get", "/v1/cli/users/me/usage")

    used = usage_data["credits_used"]
    limit = usage_data["credits_limit"]
    remaining = usage_data["credits_remaining"]
    plan = usage_data["plan"].capitalize()
    month = usage_data["month"][:7]  # YYYY-MM
    is_overdraft = usage_data["is_overdraft"]
    can_make_requests = usage_data["can_make_requests"]

    # Determine color based on status
    if is_overdraft or remaining < 0:
        remaining_color = "red"
        remaining_text = f"{remaining:,} (OVERDRAFT)"
    elif remaining < CRITICAL_CREDITS_WARNING:
        remaining_color = "red"
        remaining_text = f"{remaining:,}"
    elif remaining < LOW_CREDITS_WARNING:
        remaining_color = "yellow"
        remaining_text = f"{remaining:,}"
    else:
        remaining_color = "green"
        remaining_text = f"{remaining:,}"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Plan", f"[cyan]{plan}[/cyan]")
    table.add_row("Period", month)
    table.add_row("Used", f"{used:,} / {limit:,} credits")
    table.add_row("Remaining", f"[{remaining_color}]{remaining_text}[/{remaining_color}]")
    table.add_row("", credits_bar(used, limit, is_overdraft))

    console.print()
    console.print(f"[yellow]Credits Usage — {month}[/yellow]")
    console.print(table)

    # Show warnings
    if not can_make_requests:
        console.print()
        console.print("[bold red]⚠️  Cannot make new requests[/bold red]")
        console.print("[yellow]Your account is in overdraft. Please upgrade your plan or wait for next billing period.[/yellow]")
    elif is_overdraft or remaining < 0:
        console.print()
        console.print("[bold red]⚠️  OVERDRAFT WARNING[/bold red]")
        console.print("[yellow]Your account has exceeded the monthly limit. New requests will be blocked soon.[/yellow]")
    elif remaining < CRITICAL_CREDITS_WARNING:
        console.print()
        console.print(f"[bold red]⚠️  Almost out of credits![/bold red]")
        console.print(f"[yellow]Only {remaining} credits remaining. Consider upgrading your plan.[/yellow]")
    elif remaining < LOW_CREDITS_WARNING:
        console.print()
        console.print(f"[yellow]⚠️  Low credits: {remaining} remaining[/yellow]")

    console.print()
