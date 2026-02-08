"""Display utilities for rich console output."""
from rich import box
from rich.console import Console
from rich.panel import Panel

from gitsmart.utils.git import parse_name_status

console = Console()

STATUS_ICON = {
    "A": "[green]+[/green]",
    "M": "[yellow]~[/yellow]",
    "D": "[red]-[/red]",
    "R": "[cyan]→[/cyan]",
    "?": "[white]?[/white]",
}


def show_commit_message(message, body=None, title="Suggested Commit"):
    """Display commit message in a panel."""
    display = f"[bold yellow]{message}[/bold yellow]"
    if body:
        display += f"\n\n[yellow]{body}[/yellow]"

    console.print()
    console.print(Panel(display, title=f"[bold]{title}[/bold]", border_style="green", box=box.HORIZONTALS))


def show_file_status(repo):
    """Show git status of files (staged, unstaged, untracked)."""
    staged_raw = repo.git.diff("--staged", "--name-status")
    unstaged_raw = repo.git.diff("--name-status")
    untracked = repo.untracked_files

    staged = parse_name_status(staged_raw)
    unstaged = parse_name_status(unstaged_raw)

    console.print(f"[bold white]Changes to be committed:[/bold white]")
    for status, path in staged:
        icon = STATUS_ICON.get(status, " ")
        console.print(f"  {icon} [white]{path}[/white]")

    if unstaged or untracked:
        console.print(f"\n[bold white]Not staged:[/bold white]")
        for status, path in unstaged:
            icon = STATUS_ICON.get(status, " ")
            console.print(f"  {icon} [white dim]{path}[/white dim]")
        for path in untracked:
            console.print(f"  {STATUS_ICON['?']} [white dim]{path}[/white dim]")

    console.print()


def format_commit_parts(full_commit):
    """Split commit message into (first_line, body)."""
    lines = full_commit.splitlines()
    if not lines:
        return "", None
    message = lines[0]
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else None
    return message, body
