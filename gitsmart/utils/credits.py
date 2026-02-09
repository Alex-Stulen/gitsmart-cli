"""Credits management utilities."""
import sys

from rich.console import Console

from gitsmart.client import GitSmartClient
from gitsmart.config import LOW_CREDITS_WARNING, CRITICAL_CREDITS_WARNING
from gitsmart.utils.api import call_api

console = Console()


def get_credits_usage(client=None):
    """Fetch current credits usage from API."""
    if client is None:
        client = GitSmartClient()
    return call_api(client, "get", "/v1/cli/users/me/usage", status_message="Checking credits...")


def get_credits_warning_level(credits_remaining, is_overdraft):
    """
    Determine warning level based on remaining credits.

    Returns:
        str: "critical", "low", "normal", or "overdraft"
    """
    if is_overdraft or credits_remaining < 0:
        return "overdraft"
    elif credits_remaining < CRITICAL_CREDITS_WARNING:
        return "critical"
    elif credits_remaining < LOW_CREDITS_WARNING:
        return "low"
    else:
        return "normal"


def display_credits_status(usage_data, show_details=True):
    """
    Display credits status with warnings.

    Args:
        usage_data: Usage data from API
        show_details: Show detailed breakdown
    """
    credits_used = usage_data["credits_used"]
    credits_limit = usage_data["credits_limit"]
    credits_remaining = usage_data["credits_remaining"]
    is_overdraft = usage_data["is_overdraft"]
    can_make_requests = usage_data["can_make_requests"]
    plan = usage_data["plan"].capitalize()

    warning_level = get_credits_warning_level(credits_remaining, is_overdraft)

    # Determine color based on warning level
    if warning_level == "overdraft":
        color = "red"
        status_icon = "⚠️"
        status_text = "OVERDRAFT"
    elif warning_level == "critical":
        color = "red"
        status_icon = "⚠️"
        status_text = ""
    elif warning_level == "low":
        color = "yellow"
        status_icon = "⚠️"
        status_text = ""
    else:
        color = "green"
        status_icon = "✓"
        status_text = ""

    # Display compact status
    if is_overdraft:
        console.print(
            f"{status_icon} [{color}] {plan} plan: {credits_used}/{credits_limit} credits "
            f"({status_text}: {credits_remaining})[/{color}]"
        )
    else:
        console.print(
            f"{status_icon} [{color}] {plan} plan: {credits_remaining}/{credits_limit} credits remaining[/{color}]"
        )

    # Show warnings
    if not can_make_requests:
        console.print(
            "[bold red]❌ Cannot make new requests[/bold red]\n"
            "[yellow]   Your account is in overdraft. Please upgrade your plan or wait for next billing period.[/yellow]"
        )
    elif warning_level == "critical":
        console.print(
            f"[yellow]⚠️  Almost out of credits! Only {credits_remaining} remaining.[/yellow]"
        )
    elif warning_level == "low":
        console.print(
            f"[yellow]⚠️  Low credits warning: {credits_remaining} remaining.[/yellow]"
        )


def check_credits_before_operation(operation_name="operation"):
    """
    Pre-flight check before expensive operations.
    Displays credits status and blocks if insufficient.

    Args:
        operation_name: Name of operation for error messages

    Returns:
        dict: Usage data if check passes (use this for cost calculation later)

    Exits with error if insufficient credits.
    """
    usage_data = get_credits_usage()

    can_make_requests = usage_data["can_make_requests"]
    is_overdraft = usage_data["is_overdraft"]
    credits_remaining = usage_data["credits_remaining"]

    # Display status
    display_credits_status(usage_data, show_details=False)
    console.print()

    # Block if cannot make requests
    if not can_make_requests:
        console.print(
            f"[red]✗ Cannot perform {operation_name}[/red]\n"
            f"[yellow]Your account is in overdraft (balance: {credits_remaining} credits).[/yellow]\n"
            "[white]Please upgrade your plan or wait for the next billing period.[/white]"
        )
        sys.exit(1)

    return usage_data


def display_operation_cost(usage_before):
    """
    Display operation cost after completion.
    Fetches new usage data and calculates difference.

    Args:
        usage_before: Usage data from before the operation (from check_credits_before_operation)
    """
    try:
        usage_after = get_credits_usage()
    except Exception:
        # If we can't fetch usage after, just skip cost display
        return

    credits_before = usage_before["credits_remaining"]
    credits_after = usage_after["credits_remaining"]
    credits_limit = usage_after["credits_limit"]

    # Calculate cost (credits consumed)
    cost = credits_before - credits_after

    if cost <= 0:
        # No credits consumed or error in calculation, skip display
        return

    # Determine color based on new balance
    if credits_after < 0:
        balance_color = "red"
        balance_text = f"{credits_after} (OVERDRAFT)"
    elif credits_after < CRITICAL_CREDITS_WARNING:
        balance_color = "red"
        balance_text = f"{credits_after}/{credits_limit}"
    elif credits_after < LOW_CREDITS_WARNING:
        balance_color = "yellow"
        balance_text = f"{credits_after}/{credits_limit}"
    else:
        balance_color = "green"
        balance_text = f"{credits_after}/{credits_limit}"

    console.print(
        f"💰 [cyan]Cost:[/cyan] {cost} credit{'s' if cost != 1 else ''} | "
        f"[{balance_color}]Balance: {balance_text}[/{balance_color}]"
    )
