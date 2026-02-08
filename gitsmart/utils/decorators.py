"""Decorators for common validation checks."""
import sys
from functools import wraps

import click
from git import InvalidGitRepositoryError, Repo
from rich.console import Console

from gitsmart.config import get_api_key, get_commit_language
from gitsmart.lang import is_valid_language

console = Console()


def require_api_key(func):
    """Decorator to ensure API key is configured."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not get_api_key():
            console.print(
                "[yellow]No API key configured. Run [bold]gitsmart configure[/bold] first.[/yellow]"
            )
            sys.exit(1)
        return func(*args, **kwargs)
    return wrapper


def require_git_repo(func):
    """Decorator to ensure command runs inside a git repository."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            repo = Repo(search_parent_directories=True)
            return func(*args, repo=repo, **kwargs)
        except InvalidGitRepositoryError:
            console.print("[red]✗ Not inside a git repository.[/red]")
            sys.exit(1)
    return wrapper


def validate_language(func):
    """Decorator to validate language parameter."""
    @wraps(func)
    def wrapper(*args, lang=None, **kwargs):
        if lang is not None and not is_valid_language(lang):
            console.print(f"[red]✗ '{lang}' is not a valid ISO 639-1 language code.[/red]")
            sys.exit(1)
        language = lang.lower() if lang else get_commit_language()
        return func(*args, lang=lang, language=language, **kwargs)
    return wrapper
