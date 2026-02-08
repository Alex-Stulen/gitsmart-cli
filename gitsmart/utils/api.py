"""API interaction utilities."""
import sys

from rich.console import Console

from gitsmart.client import GitSmartAPIError, GitSmartClient

console = Console()


def call_api(client, method, path, data=None, timeout=None, status_message="Processing..."):
    """
    Call API with error handling and status display.

    Args:
        client: GitSmartClient instance
        method: HTTP method ("get" or "post")
        path: API endpoint path
        data: Request data (for POST)
        timeout: Request timeout
        status_message: Status message to display

    Returns:
        API response data
    """
    try:
        with console.status(f"[cyan]{status_message}[/cyan]"):
            if method.lower() == "get":
                return client.get(path, timeout=timeout)
            elif method.lower() == "post":
                return client.post(path, data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
    except GitSmartAPIError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)
