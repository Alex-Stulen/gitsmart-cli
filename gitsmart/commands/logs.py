"""Logs command - view usage history."""
import sys
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table

from gitsmart.client import GitSmartClient
from gitsmart.utils.api import call_api
from gitsmart.utils.decorators import require_api_key

console = Console()


def format_datetime(iso_string):
    """Format ISO datetime to readable format."""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_string


def format_response_time(ms):
    """Format response time in a readable way."""
    if ms < 1000:
        return f"{ms}ms"
    else:
        seconds = ms / 1000
        return f"{seconds:.1f}s"


def format_tokens(input_tokens, output_tokens):
    """Format token counts."""
    # Handle None values (for failed operations or old logs)
    input_tokens = input_tokens or 0
    output_tokens = output_tokens or 0
    total = input_tokens + output_tokens
    return f"{input_tokens:,}→{output_tokens:,} ({total:,})"


def fetch_logs(client, limit=20, offset=0, operation_type=None, failed_only=False):
    """
    Fetch usage logs from API.

    Args:
        client: GitSmartClient instance
        limit: Number of logs to fetch
        offset: Pagination offset
        operation_type: Filter by operation type (commit/review/analyze)
        failed_only: Show only failed operations

    Returns:
        dict: Response with logs, total, has_more, etc.
    """
    params = {"limit": limit, "offset": offset}
    if operation_type:
        params["operation_type"] = operation_type
    if failed_only:
        params["success"] = "false"

    path = "/v1/cli/users/me/usage/logs"
    if params:
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        path = f"{path}?{query_string}"

    return call_api(client, "get", path, status_message="Fetching logs...")


def display_logs_table(logs, detailed=False):
    """
    Display logs in a table format.

    Args:
        logs: List of log entries
        detailed: Show detailed information (tokens, response time)
    """
    if not logs:
        console.print("[yellow]No logs found.[/yellow]")
        return

    if detailed:
        # Detailed table with tokens and timing
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Request ID", style="dim")
        table.add_column("Date/Time", style="dim")
        table.add_column("Operation", style="cyan")
        table.add_column("Credits", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Tokens (in→out)", justify="right", style="dim")
        table.add_column("Time", justify="right", style="dim")
        table.add_column("Balance", justify="right")
    else:
        # Simple table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Request ID", style="dim")
        table.add_column("Date/Time", style="dim")
        table.add_column("Operation", style="cyan")
        table.add_column("Credits", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Balance", justify="right")

    for log in logs:
        req_id = log["id"]
        date_time = format_datetime(log["created_at"])
        operation = log["operation_type"].capitalize()
        credits = str(log["credits_charged"])
        status = "[green]✓[/green]" if log["success"] else "[red]✗[/red]"
        balance = f"{log['balance_after']}"

        if detailed:
            tokens = format_tokens(log["input_tokens"], log["output_tokens"])
            response_time = format_response_time(log["response_time_ms"])
            table.add_row(req_id, date_time, operation, credits, status, tokens, response_time, balance)
        else:
            table.add_row(req_id, date_time, operation, credits, status, balance)

    console.print()
    console.print(table)
    console.print()


def interactive_pagination(client, initial_limit, operation_type, failed_only, detailed):
    """
    Interactive pagination mode with +/- navigation.

    Args:
        client: GitSmartClient instance
        initial_limit: Number of logs per page
        operation_type: Filter by operation type
        failed_only: Show only failed operations
        detailed: Show detailed information
    """
    offset = 0
    limit = initial_limit

    while True:
        # Fetch logs for current page
        try:
            data = fetch_logs(client, limit, offset, operation_type, failed_only)
        except Exception as e:
            console.print(f"[red]✗ Failed to fetch logs: {e}[/red]")
            sys.exit(1)

        logs = data["logs"]
        total = data["total"]
        has_more = data.get("has_more", False)

        # Display table
        display_logs_table(logs, detailed)

        # Display pagination info
        showing_from = offset + 1
        showing_to = min(offset + len(logs), total)
        console.print(f"[dim]Showing {showing_from}-{showing_to} of {total} total logs[/dim]")
        console.print()

        # Display navigation options
        can_go_prev = offset > 0
        can_go_next = has_more

        console.print('[yellow]Commands:[/yellow]')
        nav_options = []

        if can_go_next:
            nav_options.append("[green][+][/green] Next page")
        if can_go_prev:
            nav_options.append("[yellow][-][/yellow] Previous page")
        nav_options.append("[red][q][/red] Q/q - quit")

        console.print(" | ".join(nav_options))
        console.print()

        # Get user input
        try:
            user_input = input("Enter command: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Exited.[/yellow]")
            sys.exit(0)

        # Process command
        if user_input == "q":
            console.print("[yellow]Exited.[/yellow]")
            break
        elif user_input == "+" and can_go_next:
            offset += limit
        elif user_input == "-" and can_go_prev:
            offset = max(0, offset - limit)
        elif user_input == "+":
            console.print("[red]✗ No more logs to show.[/red]\n")
        elif user_input == "-":
            console.print("[red]✗ Already at the first page.[/red]\n")
        else:
            console.print(f"[red]✗ Invalid command: '{user_input}'. Use +, -, or q.[/red]\n")


@click.command()
@click.option("--limit", default=20, type=int, help="Number of logs to show per page (default: 20).")
@click.option("--offset", default=0, type=int, help="Pagination offset (default: 0).")
@click.option("--type", "operation_type", default=None, help="Filter by operation type (commit/review/analyze).")
@click.option("--failed", is_flag=True, help="Show only failed operations.")
@click.option("--detail", "-d", "detailed", is_flag=True, help="Show detailed information (tokens, response time).")
@require_api_key
def logs(limit, offset, operation_type, failed, detailed):
    """View usage history and operation logs."""
    client = GitSmartClient()

    # If offset is 0 (default), use interactive mode
    if offset == 0:
        interactive_pagination(client, limit, operation_type, failed, detailed)
    else:
        # Non-interactive mode with specific offset
        data = fetch_logs(client, limit, offset, operation_type, failed)
        logs_list = data["logs"]
        display_logs_table(logs_list, detailed)

        total = data["total"]
        showing_from = offset + 1
        showing_to = min(offset + len(logs_list), total)
        console.print(f"[dim]Showing {showing_from}-{showing_to} of {total} total logs[/dim]")
        console.print()
