"""Interactive prompt utilities."""
import sys

import click
from git import GitCommandError
from rich.console import Console

console = Console()


def confirm_commit(repo, full_commit, message):
    """
    Prompt user to confirm, edit, or abort a commit.
    Returns True if committed, False if aborted.
    """
    answer = click.prompt("  Commit? [Y/n/e]", default="y", show_default=False)
    answer = answer.strip().lower()

    if answer in ("y", ""):
        do_commit(repo, full_commit)
        console.print(f"[green]✓[/green] Committed: [yellow]{message}[/yellow]\n")
        return True
    elif answer == "e":
        edited = click.edit(full_commit)
        if edited and edited.strip():
            do_commit(repo, edited.strip())
            console.print("[green]✓[/green] Committed.\n")
            return True
        else:
            console.print("[yellow]Aborted.[/yellow]\n")
            return False
    else:
        console.print("[yellow]Aborted.[/yellow]\n")
        return False


def do_commit(repo, message):
    """Execute git commit with the given message."""
    try:
        repo.git.commit("-m", message)
    except GitCommandError as e:
        console.print(f"[red]✗ Git commit failed: {e}[/red]")
        sys.exit(1)
