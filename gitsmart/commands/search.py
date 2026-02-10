"""Search command - semantic search through git history."""
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gitsmart.client import GitSmartClient, GitSmartAPIError
from gitsmart.config import (
    SEARCH_MAX_COMMITS,
    SEARCH_MIN_QUERY_LENGTH,
    SEARCH_MAX_QUERY_LENGTH,
    SEARCH_DEFAULT_LIMIT,
    SEARCH_PAGE_SIZE,
    TIMEOUT_SEARCH
)
from gitsmart.utils.api import call_api
from gitsmart.utils.credits import check_credits_before_operation, display_operation_cost
from gitsmart.utils.decorators import require_api_key, require_git_repo, validate_language
from gitsmart.utils.search import (
    get_repository_url,
    collect_commits,
    format_commit_date,
    format_relevance_bar
)

console = Console()


def validate_query(query):
    """Validate search query length."""
    if len(query) < SEARCH_MIN_QUERY_LENGTH:
        console.print(f"[red]✗ Query too short[/red]")
        console.print(f"\n   Minimum {SEARCH_MIN_QUERY_LENGTH} characters required.\n")
        console.print("   Example:")
        console.print('   [dim]gitsmart search "when was auth.py last modified?"[/dim]\n')
        sys.exit(1)

    if len(query) > SEARCH_MAX_QUERY_LENGTH:
        console.print(f"[red]✗ Query too long[/red]")
        console.print(f"\n   Maximum {SEARCH_MAX_QUERY_LENGTH} characters allowed.\n")
        sys.exit(1)


def display_answer(answer):
    """Display the AI answer in a panel."""
    panel = Panel(
        answer,
        title="[bold green]Answer[/bold green]",
        border_style="green",
        padding=(1, 2)
    )
    console.print()
    console.print(panel)
    console.print()


def display_commits_page(commits, page, page_size, total_pages):
    """
    Display a page of relevant commits.

    Args:
        commits: List of all commits to display (already limited)
        page: Current page number (0-indexed)
        page_size: Commits per page
        total_pages: Total number of pages
    """
    start = page * page_size
    end = start + page_size
    page_commits = commits[start:end]

    # Build table content
    content_lines = []

    for i, commit in enumerate(page_commits, start=start + 1):
        # Header: [N] hash | date | author <email>
        header = f"[yellow][{i}][/yellow] {commit['hash']} | {format_commit_date(commit['date'])} | {commit['author']} <{commit['email']}>"
        content_lines.append(header)

        # Relevance bar
        score = commit['relevance_score']
        bar = format_relevance_bar(score)
        relevance_line = f"Relevance: {bar}"
        content_lines.append(relevance_line)
        content_lines.append("")

        # Message (first 3 lines)
        message_lines = commit['message'].split('\n')[:3]
        content_lines.append("[yellow]Commit message:[/yellow]")
        for line in message_lines:
            if line.strip():
                content_lines.append(line)
        content_lines.append("")

        # Files (max 5)
        content_lines.append("Files:")
        files_to_show = commit['files_changed'][:5]
        for file_info in files_to_show:
            additions = file_info['additions']
            deletions = file_info['deletions']
            content_lines.append(f"  • {file_info['path']} (+{additions} -{deletions})")

        if len(commit['files_changed']) > 5:
            remaining = len(commit['files_changed']) - 5
            content_lines.append(f"  • ... and {remaining} more file{'s' if remaining > 1 else ''}")

        content_lines.append("")

        # Why relevant
        content_lines.append("Why relevant:")
        reason_lines = commit['reason'].split('\n')
        for line in reason_lines:
            if line.strip():
                content_lines.append(line)

        # Separator (if not last commit on page)
        if i < start + len(page_commits):
            content_lines.append("")
            content_lines.append("─" * 65)
            content_lines.append("")

    # Remove trailing separator if present
    while content_lines and (not content_lines[-1].strip() or "─" in content_lines[-1]):
        content_lines.pop()

    # Create panel
    title = f"[bold cyan]Relevant Commits (Page {page + 1} of {total_pages})[/bold cyan]"
    panel = Panel(
        "\n".join(content_lines),
        title=title,
        border_style="cyan",
        padding=(1, 2)
    )

    console.print(panel)


def paginate_commits(commits, limit=SEARCH_DEFAULT_LIMIT):
    """
    Interactive pagination for commits using input-based navigation.

    Args:
        commits: List of all relevant commits
        limit: Maximum commits to show (total)
    """
    # Limit total commits to display
    commits_to_show = commits[:limit]

    if not commits_to_show:
        return

    # Calculate pagination
    total_pages = (len(commits_to_show) + SEARCH_PAGE_SIZE - 1) // SEARCH_PAGE_SIZE
    current_page = 0

    # If only 1 page, just display and return
    if total_pages == 1:
        display_commits_page(commits_to_show, 0, SEARCH_PAGE_SIZE, 1)
        return

    # Multi-page pagination loop
    while True:
        # Clear screen (optional - can remove if not desired)
        # console.clear()

        # Display current page
        display_commits_page(commits_to_show, current_page, SEARCH_PAGE_SIZE, total_pages)
        console.print()

        # Navigation info
        can_go_prev = current_page > 0
        can_go_next = current_page < total_pages - 1

        console.print("[yellow]Navigation:[/yellow]")
        nav_options = []

        if can_go_next:
            nav_options.append("[green][+][/green] Next page")
        if can_go_prev:
            nav_options.append("[yellow][-][/yellow] Previous page")
        nav_options.append("[red][q][/red] Quit")

        console.print(" | ".join(nav_options))
        console.print()

        # Get user input
        try:
            user_input = input("Enter command: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Exited.[/yellow]")
            break

        # Process command
        if user_input == "q":
            console.print("[yellow]Exited.[/yellow]")
            break
        elif user_input == "+" and can_go_next:
            current_page += 1
        elif user_input == "-" and can_go_prev:
            current_page -= 1
        elif user_input == "+":
            console.print("[red]✗ No more pages to show.[/red]\n")
        elif user_input == "-":
            console.print("[red]✗ Already at the first page.[/red]\n")
        else:
            console.print(f"[red]✗ Invalid command: '{user_input}'. Use +, -, or q.[/red]\n")


@click.command()
@click.argument('query')
@click.option('--author', help='Filter by author name')
@click.option('--email', help='Filter by author email')
@click.option('--lang', help='Response language (en/ru/uk)')
@click.option('--branch', help='Branch to analyze (default: current)')
@click.option('--limit', type=int, help=f'Max commits to display (default: {SEARCH_DEFAULT_LIMIT})')
@validate_language
@require_git_repo
@require_api_key
def search(query, author, email, lang, branch, limit, repo, language):
    """
    Search through git history using AI.

    Examples:

      gitsmart search "when was auth.py last modified?"

      gitsmart search "bug fixes by Ivan" --author "Ivan"

      gitsmart search "recent changes" --lang ru --limit 10
    """
    # Validate query
    validate_query(query)

    # Check credits before operation
    usage_before = check_credits_before_operation("search")

    # Get repository URL
    try:
        repository_url = get_repository_url(repo)
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        console.print("\n   Add a remote with:")
        console.print("   [dim]git remote add origin <url>[/dim]\n")
        sys.exit(1)

    # Determine branch
    if branch:
        # Validate branch exists
        try:
            repo.commit(branch)
        except Exception:
            console.print(f"[red]✗ Branch '{branch}' not found[/red]\n")
            branches = [b.name for b in repo.branches]
            if branches:
                console.print("   Available branches:")
                for b in branches[:10]:  # Show max 10
                    console.print(f"   • {b}")
                if len(branches) > 10:
                    console.print(f"   • ... and {len(branches) - 10} more")
            console.print()
            sys.exit(1)
    else:
        # Use current branch
        branch = repo.active_branch.name

    # Get anchor from API
    client = GitSmartClient()
    try:
        with console.status("[cyan]🔍 Checking for updates...[/cyan]"):
            anchor = client.get_search_anchor(repository_url, timeout=TIMEOUT_SEARCH)
    except GitSmartAPIError as e:
        if e.status_code == 503:
            console.print("[red]✗ Search service temporarily unavailable[/red]")
            console.print("\n   Please try again later.\n")
        else:
            console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    anchor_hash = anchor.get("full_hash")

    # Collect commits
    try:
        with console.status("[cyan]🔍 Collecting git history...[/cyan]"):
            commits = collect_commits(repo, branch, anchor_hash, SEARCH_MAX_COMMITS)
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    # Note: It's OK if commits is empty - API will search in existing RAG database
    # Only show info message if this is the first time (no anchor) and no commits
    if not commits and anchor_hash is None:
        console.print("[yellow]⚠ Branch has no commits to analyze.[/yellow]")
        sys.exit(0)

    # Show info about current limitations
    console.print(f"[dim]ℹ️  Currently analyzing up to {SEARCH_MAX_COMMITS} recent commits. We're working to increase this limit![/dim]")

    # Build filters
    filters = {}
    if author:
        filters["author"] = author
    if email:
        filters["email"] = email

    # Show hint about credits
    if anchor_hash is None:
        console.print("[dim]💡 Hint: First search may use more credits due to commit history analysis.[/dim]\n")
    else:
        console.print("[dim]💡 Hint: Subsequent searches use fewer credits than the first one.[/dim]\n")

    # Call search API
    try:
        # Show hint for first search (when building index)
        if anchor_hash is None:
            status_msg = "[cyan]🤖 Analyzing commits...[/cyan]\n[dim]💡 First search always takes longer :)[/dim]"
        else:
            status_msg = "[cyan]🤖 Analyzing commits...[/cyan]"

        with console.status(status_msg):
            response = client.search_commits(
                query=query,
                repository_url=repository_url,
                commits=commits,
                language=language,
                filters=filters if filters else None,
                timeout=TIMEOUT_SEARCH
            )
    except GitSmartAPIError as e:
        if e.status_code == 402:
            console.print("[red]✗ Insufficient credits[/red]")
            console.print(f"\n   {e}\n")
            console.print("   Upgrade your plan:")
            console.print("   [dim]gitsmart billing[/dim]\n")
        elif e.status_code == 429:
            console.print("[red]✗ Too many search requests[/red]")
            console.print("\n   Rate limit: 5 searches per minute")
            console.print("   Please wait and try again.\n")
        elif e.status_code == 503:
            console.print("[red]✗ Search service temporarily unavailable[/red]")
            console.print("\n   Please try again later.\n")
        else:
            console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    # Display results
    answer = response["answer"]
    relevant_commits = response["relevant_commits"]
    total_analyzed = response["total_analyzed"]

    console.print(f"\n[green]✓[/green] Found {len(relevant_commits)} relevant commit{'s' if len(relevant_commits) != 1 else ''} from {total_analyzed} total")

    # Display answer
    display_answer(answer)

    # Display and paginate commits
    if relevant_commits:
        paginate_commits(relevant_commits, limit or SEARCH_DEFAULT_LIMIT)

    # Display cost
    console.print()
    display_operation_cost(usage_before)
