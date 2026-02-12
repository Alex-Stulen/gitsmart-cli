"""Explain command."""
import sys
import time
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from gitsmart.client import GitSmartClient
from gitsmart.config import TIMEOUT_EXPLAIN, EXPLAIN_BATCH_DELAY
from gitsmart.utils.api import call_api
from gitsmart.utils.credits import check_credits_before_operation, display_operation_cost
from gitsmart.utils.decorators import require_api_key, require_git_repo, validate_language
from gitsmart.utils.git import get_commit_data, get_commits_in_range, get_current_branch_name, get_staged_data

console = Console()


def display_explanation_rich(result):
    """Display explanation in Rich panels with formatting."""
    explanation = result["explanation"]

    # Title
    console.print()
    console.print(Panel(
        f"[bold cyan]{explanation['title']}[/bold cyan]",
        title="[yellow]📝 Commit Explanation[/yellow]",
        border_style="cyan",
        box=box.HORIZONTALS,
    ))

    # Summary
    console.print()
    console.print(Panel(
        f"[white]{explanation['summary']}[/white]",
        title="[yellow]📋 Summary[/yellow]",
        border_style="blue",
        box=box.HORIZONTALS,
    ))

    # Technical Changes
    technical_changes = explanation.get("technical_changes") or []
    if technical_changes:
        console.print()
        console.print("[bold cyan]🔧 Technical Changes:[/bold cyan]")
        for change in technical_changes:
            console.print(f"  [white]•[/white] [white]{change}[/white]")

    # Details (Markdown)
    details = explanation.get("details")
    if details:
        console.print()
        console.print(Panel(
            Markdown(details),
            title="[yellow]📖 Details[/yellow]",
            border_style="green",
            box=box.HORIZONTALS,
        ))

    # Affected Components
    affected_components = explanation.get("affected_components") or []
    if affected_components:
        console.print()
        console.print("[bold cyan]🎯 Affected Components:[/bold cyan]")
        for component in affected_components:
            console.print(f"  [white]•[/white] [cyan]{component}[/cyan]")

    # Breaking Changes Warning
    breaking_changes = explanation.get("breaking_changes", False)
    if breaking_changes:
        console.print()
        console.print(Panel(
            "[bold red]⚠️  This commit introduces BREAKING CHANGES[/bold red]",
            border_style="red",
            box=box.HORIZONTALS,
        ))

    console.print()


def display_explanation_markdown(result):
    """Display explanation as plain markdown in console."""
    explanation = result["explanation"]

    # Title
    console.print()
    console.print(f"# {explanation['title']}")
    console.print()

    # Summary
    console.print("## Summary")
    console.print()
    console.print(explanation['summary'])
    console.print()

    # Technical Changes
    technical_changes = explanation.get("technical_changes") or []
    if technical_changes:
        console.print("## Technical Changes")
        console.print()
        for change in technical_changes:
            console.print(f"- {change}")
        console.print()

    # Details
    details = explanation.get("details")
    if details:
        console.print("## Details")
        console.print()
        console.print(details)
        console.print()

    # Affected Components
    affected_components = explanation.get("affected_components") or []
    if affected_components:
        console.print("## Affected Components")
        console.print()
        for component in affected_components:
            console.print(f"- {component}")
        console.print()

    # Breaking Changes
    breaking_changes = explanation.get("breaking_changes", False)
    if breaking_changes:
        console.print("## ⚠️ Breaking Changes")
        console.print()
        console.print("This commit introduces **BREAKING CHANGES**.")
        console.print()


def format_explanation_markdown(commit_data, explanation, branch_name):
    """Format explanation as markdown for file output."""
    lines = []

    # Header
    lines.append(f"# Commit: {commit_data['hash']}")
    lines.append(f"# Full Hash: {commit_data['full_hash']}")
    lines.append(f"# Date: {commit_data['date']}")
    lines.append(f"# Branch: {branch_name or 'detached HEAD'}")
    lines.append("# Changes:")
    lines.append("")

    # Title
    lines.append(f"## {explanation['title']}")
    lines.append("")

    # Summary
    lines.append("### Summary")
    lines.append("")
    lines.append(explanation['summary'])
    lines.append("")

    # Technical Changes
    technical_changes = explanation.get("technical_changes") or []
    if technical_changes:
        lines.append("### Technical Changes")
        lines.append("")
        for change in technical_changes:
            lines.append(f"- {change}")
        lines.append("")

    # Details
    details = explanation.get("details")
    if details:
        lines.append("### Details")
        lines.append("")
        lines.append(details)
        lines.append("")

    # Affected Components
    affected_components = explanation.get("affected_components") or []
    if affected_components:
        lines.append("### Affected Components")
        lines.append("")
        for component in affected_components:
            lines.append(f"- {component}")
        lines.append("")

    # Breaking Changes
    breaking_changes = explanation.get("breaking_changes", False)
    if breaking_changes:
        lines.append("### ⚠️ Breaking Changes")
        lines.append("")
        lines.append("This commit introduces **BREAKING CHANGES**.")
        lines.append("")

    return "\n".join(lines)


def display_hints(markdown):
    """Display format and save hints if applicable."""
    console.print()

    # Format hint - only if not already in markdown mode
    if not markdown:
        console.print("[bold white]💡 Format Hint: Use [cyan]--markdown[/cyan] or [cyan]-md[/cyan] flag to display output in plain Markdown format.[/bold white]")

    # Save hint - always show (function only called when output is not specified)
    console.print("[bold white]💡 Save Hint: You can save the Markdown output to a file using [cyan]--output FILE[/cyan] or [cyan]-o FILE[/cyan] (e.g., [cyan]~/Desktop/CHANGES.md[/cyan]).[/bold white]")


def append_to_file(file_path, content):
    """Append content to file."""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(content)
        f.write("\n")


def process_single_commit(repo, commit_hash, language, markdown, output_file):
    """Process a single commit and return result."""
    # Get commit data from git
    commit_data = get_commit_data(repo, commit_hash)
    if commit_data is None:
        console.print(f"[red]✗ Commit '{commit_hash}' not found in repository.[/red]")
        sys.exit(1)

    # Prepare API request
    client = GitSmartClient()
    payload = {
        "hash": commit_data["hash"],
        "full_hash": commit_data["full_hash"],
        "author": commit_data["author"],
        "email": commit_data["email"],
        "date": commit_data["date"],
        "message": commit_data["message"],
        "files_changed": commit_data["files_changed"],
        "total_changes": commit_data["total_changes"],
        "diff": commit_data["diff"],
        "language": language,
    }

    # Call API
    result = call_api(
        client,
        "post",
        "/v1/git/explain/commit",
        payload,
        timeout=TIMEOUT_EXPLAIN,
        status_message="Analyzing commit..."
    )

    # Handle output
    if output_file:
        # Get branch name
        branch_name = get_current_branch_name(repo)

        # Format and write to file
        content = format_explanation_markdown(commit_data, result["explanation"], branch_name)
        append_to_file(output_file, content)
        append_to_file(output_file, "---")
        append_to_file(output_file, "")

        # Show success message
        console.print()
        console.print(f"[green]✓ Explanation saved to:[/green] [cyan]{output_file}[/cyan]")
    else:
        # Display in console
        if markdown:
            display_explanation_markdown(result)
        else:
            display_explanation_rich(result)

    return result


def process_commit_range(repo, from_commit, to_commit, language, output_file, exclude=None):
    """Process a range of commits and write to file."""
    # Get commits in range
    console.print(f"[cyan]📋 Getting commits from {from_commit} to {to_commit}...[/cyan]")
    commit_hashes = get_commits_in_range(repo, from_commit, to_commit)

    if commit_hashes is None:
        console.print(f"[red]✗ Invalid commit range: {from_commit}..{to_commit}[/red]")
        sys.exit(1)

    if not commit_hashes:
        console.print(f"[yellow]⚠ No commits found in range {from_commit}..{to_commit}[/yellow]")
        sys.exit(0)

    # Process exclusions if provided
    if exclude:
        # Parse comma-separated hashes
        exclude_hashes = [h.strip() for h in exclude.split(",") if h.strip()]

        if exclude_hashes:
            console.print(f"[cyan]🔍 Processing exclusions: {len(exclude_hashes)} commit(s) to check...[/cyan]")

            # Validate and normalize exclude hashes
            validated_excludes = []
            for exclude_hash in exclude_hashes:
                try:
                    # Try to resolve the hash (supports short and full hashes)
                    commit_obj = repo.commit(exclude_hash)
                    full_hash = commit_obj.hexsha

                    # Check if commit is in the range
                    if full_hash in commit_hashes:
                        validated_excludes.append(full_hash)
                        console.print(f"[yellow]  ⊖ Excluding: {exclude_hash[:7]} (found in range)[/yellow]")
                    else:
                        console.print(f"[yellow]  ⚠ Warning: {exclude_hash[:7]} not in range {from_commit}..{to_commit}, ignoring[/yellow]")
                except Exception:
                    console.print(f"[yellow]  ⚠ Warning: {exclude_hash} is not a valid commit hash, ignoring[/yellow]")

            # Filter out excluded commits
            if validated_excludes:
                original_count = len(commit_hashes)
                commit_hashes = [h for h in commit_hashes if h not in validated_excludes]
                excluded_count = original_count - len(commit_hashes)
                console.print(f"[cyan]✓ Excluded {excluded_count} commit(s)[/cyan]")

            console.print()

    if not commit_hashes:
        console.print(f"[yellow]⚠ No commits left to process after exclusions[/yellow]")
        sys.exit(0)

    total_commits = len(commit_hashes)
    console.print(f"[cyan]📊 Found {total_commits} commit(s) to process[/cyan]")
    console.print()

    # Check credits before starting
    usage_before = check_credits_before_operation(f"processing {total_commits} commit(s)")

    # Process each commit
    for idx, commit_hash in enumerate(commit_hashes, start=1):
        console.print(f"[bold cyan]▶ [{idx}/{total_commits}] Processing commit {commit_hash[:7]}...[/bold cyan]")

        try:
            result = process_single_commit(repo, commit_hash, language, markdown=False, output_file=output_file)
            credits_charged = result.get("credits_charged", 0)
            console.print(f"[green]✓ [{idx}/{total_commits}] {commit_hash[:7]} - {credits_charged} credits charged[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to process commit {commit_hash[:7]}: {e}[/red]")
            console.print("[red]Stopping processing due to error.[/red]")
            sys.exit(1)

        # Wait between requests (except for last commit)
        if idx < total_commits:
            console.print(f"[dim]⏱  Waiting {EXPLAIN_BATCH_DELAY} second(s)...[/dim]")
            time.sleep(EXPLAIN_BATCH_DELAY)
            console.print()

    console.print()
    console.print(f"[bold green]✓ Successfully processed {total_commits} commit(s)[/bold green]")
    console.print(f"[cyan]📁 Output saved to: {output_file}[/cyan]")
    console.print()

    # Display total cost
    display_operation_cost(usage_before)


def process_staged_changes(repo, language, markdown, output_file):
    """Process staged changes and return result."""
    # Get staged data from git
    staged_data = get_staged_data(repo)
    if staged_data is None:
        console.print("[red]✗ No staged changes found in repository.[/red]")
        console.print("[yellow]Hint: Use 'git add' to stage files before running this command.[/yellow]")
        sys.exit(1)

    # Prepare API request
    client = GitSmartClient()
    payload = {
        "files_changed": staged_data["files_changed"],
        "total_changes": staged_data["total_changes"],
        "diff": staged_data["diff"],
        "language": language,
    }

    # Call API
    result = call_api(
        client,
        "post",
        "/v1/git/explain/staged",
        payload,
        timeout=TIMEOUT_EXPLAIN,
        status_message="Analyzing staged changes..."
    )

    # Handle output
    if output_file:
        # Get branch name
        branch_name = get_current_branch_name(repo)

        # Format metadata for staged changes
        from datetime import datetime
        current_time = datetime.now().isoformat()

        # Build markdown content
        lines = []
        lines.append(f"# Staged Changes Analysis")
        lines.append(f"# Generated: {current_time}")
        lines.append(f"# Branch: {branch_name or 'detached HEAD'}")
        lines.append(f"# Total files changed: {len(staged_data['files_changed'])}")
        lines.append(f"# Total changes: {staged_data['total_changes']} lines")
        lines.append("")

        explanation = result["explanation"]

        # Title
        lines.append(f"## {explanation['title']}")
        lines.append("")

        # Summary
        lines.append("### Summary")
        lines.append("")
        lines.append(explanation['summary'])
        lines.append("")

        # Technical Changes
        technical_changes = explanation.get("technical_changes") or []
        if technical_changes:
            lines.append("### Technical Changes")
            lines.append("")
            for change in technical_changes:
                lines.append(f"- {change}")
            lines.append("")

        # Details
        details = explanation.get("details")
        if details:
            lines.append("### Details")
            lines.append("")
            lines.append(details)
            lines.append("")

        # Affected Components
        affected_components = explanation.get("affected_components") or []
        if affected_components:
            lines.append("### Affected Components")
            lines.append("")
            for component in affected_components:
                lines.append(f"- {component}")
            lines.append("")

        # Breaking Changes
        breaking_changes = explanation.get("breaking_changes", False)
        if breaking_changes:
            lines.append("### ⚠️ Breaking Changes")
            lines.append("")
            lines.append("These changes introduce **BREAKING CHANGES**.")
            lines.append("")

        content = "\n".join(lines)
        append_to_file(output_file, content)

        # Show success message
        console.print()
        console.print(f"[green]✓ Explanation saved to:[/green] [cyan]{output_file}[/cyan]")
    else:
        # Display in console
        if markdown:
            display_explanation_markdown(result)
        else:
            display_explanation_rich(result)

    return result


@click.command()
@click.option(
    "--commit", "-c",
    metavar="HASH",
    help="Single commit hash to explain.",
)
@click.option(
    "--from",
    "from_commit",
    metavar="HASH",
    help="Start commit for range (requires --to).",
)
@click.option(
    "--to",
    "to_commit",
    metavar="HASH",
    help="End commit for range (requires --from).",
)
@click.option(
    "--staged", "-s",
    is_flag=True,
    help="Explain currently staged changes (git add).",
)
@click.option(
    "--exclude", "-ex",
    metavar="HASHES",
    help="Comma-separated list of commit hashes to exclude from range (e.g., hash1,hash2,hash3).",
)
@click.option(
    "--output", "-o",
    metavar="FILE",
    help="Save explanations to markdown file (requires --markdown).",
)
@click.option(
    "--lang",
    default=None,
    metavar="LANG",
    help="Explanation language (ISO 639-1), overrides config.",
)
@click.option(
    "--markdown", "-md",
    is_flag=True,
    help="Output as plain markdown instead of Rich panels.",
)
@validate_language
@require_git_repo
@require_api_key
def explain(commit, from_commit, to_commit, staged, exclude, output, lang, markdown, repo, language):
    """Generate AI-powered explanation for a commit or commit range."""
    # Validate mutually exclusive modes
    single_mode = commit is not None
    range_mode = from_commit is not None or to_commit is not None
    staged_mode = staged

    # Count how many modes are active
    active_modes = sum([single_mode, range_mode, staged_mode])

    if active_modes > 1:
        console.print("[red]✗ Cannot combine --commit, --from/--to, and --staged. Choose only one mode.[/red]")
        sys.exit(1)

    if active_modes == 0:
        console.print("[red]✗ No mode specified. Choose one of the following:[/red]")
        console.print()
        console.print("  [cyan]--staged, -s[/cyan]")
        console.print("    [white]Explain currently staged changes (files added with 'git add')[/white]")
        console.print()
        console.print("  [cyan]--commit, -c HASH[/cyan]")
        console.print("    [white]Explain a single commit by its hash[/white]")
        console.print()
        console.print("  [cyan]--from HASH --to HASH[/cyan]")
        console.print("    [white]Explain a range of commits (both flags required)[/white]")
        console.print()
        sys.exit(1)

    # Validate exclude flag (only for range mode)
    if exclude and not range_mode:
        console.print("[red]✗ --exclude can only be used with --from/--to range mode.[/red]")
        sys.exit(1)

    # Validate range mode requirements
    if range_mode:
        if from_commit is None or to_commit is None:
            console.print("[red]✗ Both --from and --to are required for range mode.[/red]")
            sys.exit(1)

        if output is None:
            console.print("[red]✗ --output is required when using --from/--to range mode.[/red]")
            sys.exit(1)

        if not markdown:
            console.print("[red]✗ --markdown flag is required when using --output.[/red]")
            sys.exit(1)

    # Validate output file extension and directory
    if output:
        output_path = Path(output)
        if output_path.suffix.lower() != ".md":
            console.print("[red]✗ Output file must have .md extension.[/red]")
            sys.exit(1)

        # Ensure parent directory exists
        parent_dir = output_path.parent
        if not parent_dir.exists():
            # Ask user permission to create directory
            if not click.confirm(f"Directory '{parent_dir}' does not exist. Create it?", default=True):
                console.print("[yellow]Operation cancelled.[/yellow]")
                sys.exit(0)

            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
                console.print(f"[cyan]✓ Created directory: {parent_dir}[/cyan]")
            except Exception as e:
                console.print(f"[red]✗ Failed to create directory '{parent_dir}': {e}[/red]")
                sys.exit(1)

        # Check if file exists and ask for confirmation
        if output_path.exists():
            if not click.confirm(f"File '{output}' already exists. Overwrite?", default=False):
                console.print("[yellow]Operation cancelled.[/yellow]")
                sys.exit(0)
            # Clear file if overwriting
            output_path.write_text("", encoding="utf-8")

    # Execute appropriate mode
    if staged_mode:
        # Staged changes mode
        usage_before = check_credits_before_operation("staged changes explanation")
        process_staged_changes(repo, language, markdown, output)

        if not output:
            display_hints(markdown)

        display_operation_cost(usage_before)
    elif range_mode:
        # Commit range mode
        process_commit_range(repo, from_commit, to_commit, language, output, exclude)
    else:
        # Single commit mode
        usage_before = check_credits_before_operation("commit explanation")
        process_single_commit(repo, commit, language, markdown, output)

        if not output:
            display_hints(markdown)

        display_operation_cost(usage_before)
