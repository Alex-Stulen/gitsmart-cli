"""Security analysis command."""
import sys
import time
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from gitsmart.client import GitSmartClient
from gitsmart.config import TIMEOUT_SECURITY, SECURITY_BATCH_DELAY, HINT_MAX_LENGTH
from gitsmart.utils.api import call_api
from gitsmart.utils.credits import check_credits_before_operation, display_operation_cost
from gitsmart.utils.decorators import require_api_key, require_git_repo, validate_language
from gitsmart.utils.git import get_commit_data, get_commits_in_range, get_current_branch_name, get_staged_data

console = Console()


# Severity colors and emojis
SEVERITY_STYLES = {
    "critical": {"color": "red", "emoji": "🚨", "label": "CRITICAL"},
    "high": {"color": "orange1", "emoji": "⚠️", "label": "HIGH"},
    "medium": {"color": "yellow", "emoji": "⚡", "label": "MEDIUM"},
    "low": {"color": "cyan", "emoji": "ℹ️", "label": "LOW"},
}


def display_security_issue(issue, markdown=False):
    """Display a single security issue."""
    severity = issue.get("severity", "low")
    style = SEVERITY_STYLES.get(severity, SEVERITY_STYLES["low"])

    if markdown:
        # Markdown format
        lines = []
        lines.append(f"### {style['emoji']} {issue['title']}")
        lines.append(f"**Severity:** {severity.upper()}")

        if issue.get("location"):
            lines.append(f"**Location:** `{issue['location']}`")

        if issue.get("cwe_id"):
            cwe_url = f"https://cwe.mitre.org/data/definitions/{issue['cwe_id'].replace('CWE-', '')}.html"
            lines.append(f"**CWE:** [{issue['cwe_id']}]({cwe_url})")

        lines.append("")
        lines.append(issue["description"])
        lines.append("")
        lines.append(f"**Recommendation:** {issue['recommendation']}")

        return "\n".join(lines)
    else:
        # Rich format
        content_lines = []

        # Severity badge
        severity_badge = f"[bold {style['color']}]{style['emoji']} {style['label']}[/bold {style['color']}]"
        content_lines.append(severity_badge)
        content_lines.append("")

        # Location
        if issue.get("location"):
            content_lines.append(f"[yellow]Location:[/yellow] [cyan]{issue['location']}[/cyan]")

        # CWE ID
        if issue.get("cwe_id"):
            cwe_url = f"https://cwe.mitre.org/data/definitions/{issue['cwe_id'].replace('CWE-', '')}.html"
            content_lines.append(f"[yellow]CWE:[/yellow] [{issue['cwe_id']}]({cwe_url})")

        if issue.get("location") or issue.get("cwe_id"):
            content_lines.append("")

        # Description
        content_lines.append(f"[white]{issue['description']}[/white]")
        content_lines.append("")

        # Recommendation
        content_lines.append(f"[bold green]Recommendation:[/bold green]")
        content_lines.append(f"[green]{issue['recommendation']}[/green]")

        content = "\n".join(content_lines)

        console.print(Panel(
            content,
            title=f"[yellow]{issue['title']}[/yellow]",
            border_style=style['color'],
            box=box.HORIZONTALS,
        ))


def display_security_result_rich(result):
    """Display security analysis result in Rich panels with formatting."""
    analysis = result

    # Header
    console.print()

    # Check if there are any issues
    has_critical = len(analysis.get("critical_issues", [])) > 0
    has_warnings = len(analysis.get("warnings", [])) > 0

    if not has_critical and not has_warnings:
        # No issues found - success message
        console.print(Panel(
            "[bold green]✓ No security issues detected. Good job![/bold green]",
            border_style="green",
            box=box.HORIZONTALS,
        ))

    # Summary (always show)
    console.print()
    console.print(Panel(
        f"[white]{analysis['summary']}[/white]",
        title="[yellow]📋 Security Analysis Summary[/yellow]",
        border_style="blue",
        box=box.HORIZONTALS,
    ))

    # Critical Issues (separate section at top)
    critical_issues = analysis.get("critical_issues", [])
    if critical_issues:
        console.print()
        console.print(Panel(
            f"[bold red]Found {len(critical_issues)} critical security issue(s) - immediate attention required![/bold red]",
            border_style="red",
            box=box.HORIZONTALS,
        ))
        console.print()

        for issue in critical_issues:
            display_security_issue(issue, markdown=False)
            console.print()

    # Warnings (grouped by severity)
    warnings = analysis.get("warnings", [])
    if warnings:
        # Group by severity
        grouped_warnings = {"high": [], "medium": [], "low": []}
        for warning in warnings:
            severity = warning.get("severity", "low")
            if severity in grouped_warnings:
                grouped_warnings[severity].append(warning)

        # Display each severity group
        for severity in ["high", "medium", "low"]:
            issues = grouped_warnings[severity]
            if issues:
                style = SEVERITY_STYLES[severity]
                console.print(f"[bold {style['color']}]{style['emoji']} {style['label']} Severity ({len(issues)} issue(s)):[/bold {style['color']}]")
                console.print()

                for issue in issues:
                    display_security_issue(issue, markdown=False)
                    console.print()

    # Recommendations
    recommendations = analysis.get("recommendations", [])
    if recommendations:
        console.print(Panel(
            "\n".join([f"• {rec}" for rec in recommendations]),
            title="[yellow]💡 General Security Recommendations[/yellow]",
            border_style="cyan",
            box=box.HORIZONTALS,
        ))
        console.print()


def display_security_result_markdown(result):
    """Display security analysis result as plain markdown in console."""
    analysis = result

    console.print()

    # Header
    has_critical = len(analysis.get("critical_issues", [])) > 0
    has_warnings = len(analysis.get("warnings", [])) > 0

    if not has_critical and not has_warnings:
        console.print("# ✓ No security issues detected. Good job!")
        console.print()
    else:
        console.print("# Security Analysis Report")
        console.print()

    # Summary
    console.print("## Summary")
    console.print()
    console.print(analysis['summary'])
    console.print()

    # Critical Issues
    critical_issues = analysis.get("critical_issues", [])
    if critical_issues:
        console.print(f"## 🚨 Critical Issues ({len(critical_issues)})")
        console.print()
        console.print("**⚠️ IMMEDIATE ATTENTION REQUIRED**")
        console.print()

        for issue in critical_issues:
            console.print(display_security_issue(issue, markdown=True))
            console.print()

    # Warnings (grouped by severity)
    warnings = analysis.get("warnings", [])
    if warnings:
        # Group by severity
        grouped_warnings = {"high": [], "medium": [], "low": []}
        for warning in warnings:
            severity = warning.get("severity", "low")
            if severity in grouped_warnings:
                grouped_warnings[severity].append(warning)

        # Display each severity group
        for severity in ["high", "medium", "low"]:
            issues = grouped_warnings[severity]
            if issues:
                style = SEVERITY_STYLES[severity]
                console.print(f"## {style['emoji']} {style['label']} Severity ({len(issues)})")
                console.print()

                for issue in issues:
                    console.print(display_security_issue(issue, markdown=True))
                    console.print()

    # Recommendations
    recommendations = analysis.get("recommendations", [])
    if recommendations:
        console.print("## 💡 Recommendations")
        console.print()
        for rec in recommendations:
            console.print(f"- {rec}")
        console.print()


def format_security_markdown(commit_data, analysis, branch_name):
    """Format security analysis as markdown for file output."""
    lines = []

    # Header
    lines.append(f"# Security Analysis: {commit_data['hash']}")
    lines.append(f"# Full Hash: {commit_data['full_hash']}")
    lines.append(f"# Date: {commit_data['date']}")
    lines.append(f"# Branch: {branch_name or 'detached HEAD'}")
    lines.append("")

    # Check if there are issues
    has_critical = len(analysis.get("critical_issues", [])) > 0
    has_warnings = len(analysis.get("warnings", [])) > 0

    if not has_critical and not has_warnings:
        lines.append("## ✓ No Security Issues Detected. Good job!")
        lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(analysis['summary'])
    lines.append("")

    # Critical Issues
    critical_issues = analysis.get("critical_issues", [])
    if critical_issues:
        lines.append(f"## 🚨 Critical Issues ({len(critical_issues)})")
        lines.append("")
        lines.append("**⚠️ IMMEDIATE ATTENTION REQUIRED**")
        lines.append("")

        for i, issue in enumerate(critical_issues, 1):
            lines.append(f"### {i}. {issue['title']}")
            lines.append(f"**Severity:** CRITICAL")

            if issue.get("location"):
                lines.append(f"**Location:** `{issue['location']}`")

            if issue.get("cwe_id"):
                cwe_url = f"https://cwe.mitre.org/data/definitions/{issue['cwe_id'].replace('CWE-', '')}.html"
                lines.append(f"**CWE:** [{issue['cwe_id']}]({cwe_url})")

            lines.append("")
            lines.append(issue["description"])
            lines.append("")
            lines.append(f"**Recommendation:** {issue['recommendation']}")
            lines.append("")

    # Warnings (grouped by severity)
    warnings = analysis.get("warnings", [])
    if warnings:
        # Group by severity
        grouped_warnings = {"high": [], "medium": [], "low": []}
        for warning in warnings:
            severity = warning.get("severity", "low")
            if severity in grouped_warnings:
                grouped_warnings[severity].append(warning)

        # Display each severity group
        for severity in ["high", "medium", "low"]:
            issues = grouped_warnings[severity]
            if issues:
                style = SEVERITY_STYLES[severity]
                lines.append(f"## {style['emoji']} {style['label']} Severity ({len(issues)})")
                lines.append("")

                for i, issue in enumerate(issues, 1):
                    lines.append(f"### {i}. {issue['title']}")
                    lines.append(f"**Severity:** {severity.upper()}")

                    if issue.get("location"):
                        lines.append(f"**Location:** `{issue['location']}`")

                    if issue.get("cwe_id"):
                        cwe_url = f"https://cwe.mitre.org/data/definitions/{issue['cwe_id'].replace('CWE-', '')}.html"
                        lines.append(f"**CWE:** [{issue['cwe_id']}]({cwe_url})")

                    lines.append("")
                    lines.append(issue["description"])
                    lines.append("")
                    lines.append(f"**Recommendation:** {issue['recommendation']}")
                    lines.append("")

    # Recommendations
    recommendations = analysis.get("recommendations", [])
    if recommendations:
        lines.append("## 💡 Recommendations")
        lines.append("")
        for rec in recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    return "\n".join(lines)


def display_hints(markdown):
    """Display format and save hints if applicable."""
    console.print()

    # Format hint - only if not already in markdown mode
    if not markdown:
        console.print("[bold white]💡 Format Hint: Use [cyan]--markdown[/cyan] or [cyan]-md[/cyan] flag to display output in plain Markdown format.[/bold white]")

    # Save hint - always show (function only called when output is not specified)
    console.print("[bold white]💡 Save Hint: You can save the Markdown output to a file using [cyan]--output FILE[/cyan] or [cyan]-o FILE[/cyan] (e.g., [cyan]~/Desktop/SECURITY_REPORT.md[/cyan]).[/bold white]")


def append_to_file(file_path, content):
    """Append content to file."""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(content)
        f.write("\n")


def process_single_commit(repo, commit_hash, language, hint, markdown, output_file):
    """Process security analysis for a single commit."""
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

    if hint:
        payload["ai_hint"] = hint

    # Call API
    result = call_api(
        client,
        "post",
        "/v1/git/security/commit",
        payload,
        timeout=TIMEOUT_SECURITY,
        status_message="Analyzing security..."
    )

    # Handle output
    if output_file:
        # Get branch name
        branch_name = get_current_branch_name(repo)

        # Format and write to file
        content = format_security_markdown(commit_data, result, branch_name)
        append_to_file(output_file, content)
        append_to_file(output_file, "---")
        append_to_file(output_file, "")

        # Show success message
        console.print()
        console.print(f"[green]✓ Security analysis saved to:[/green] [cyan]{output_file}[/cyan]")
    else:
        # Display in console
        if markdown:
            display_security_result_markdown(result)
        else:
            display_security_result_rich(result)

    return result


def process_staged_changes(repo, language, hint, markdown, output_file):
    """Process security analysis for staged changes."""
    # Get staged data from git
    staged_data = get_staged_data(repo)
    if staged_data is None:
        console.print("[red]✗ No staged changes found in repository.[/red]")
        console.print("[yellow]Hint: Use 'git add' to stage files before running this command.[/yellow]")
        console.print("[yellow]Or use [cyan]--commit[/cyan] or [cyan]-c[/cyan] flag to analyze a specific commit.[/yellow]")
        sys.exit(1)

    # Prepare API request
    client = GitSmartClient()
    payload = {
        "files_changed": staged_data["files_changed"],
        "total_changes": staged_data["total_changes"],
        "diff": staged_data["diff"],
        "language": language,
    }

    if hint:
        payload["ai_hint"] = hint

    # Call API
    result = call_api(
        client,
        "post",
        "/v1/git/security/staged",
        payload,
        timeout=TIMEOUT_SECURITY,
        status_message="Analyzing security of staged changes..."
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
        lines.append(f"# Security Analysis: Staged Changes")
        lines.append(f"# Generated: {current_time}")
        lines.append(f"# Branch: {branch_name or 'detached HEAD'}")
        lines.append(f"# Total files changed: {len(staged_data['files_changed'])}")
        lines.append(f"# Total changes: {staged_data['total_changes']} lines")
        lines.append("")

        # Check if there are issues
        has_critical = len(result.get("critical_issues", [])) > 0
        has_warnings = len(result.get("warnings", [])) > 0

        if not has_critical and not has_warnings:
            lines.append("## ✓ No Security Issues Detected. Good job!")
            lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(result['summary'])
        lines.append("")

        # Critical Issues
        critical_issues = result.get("critical_issues", [])
        if critical_issues:
            lines.append(f"## 🚨 Critical Issues ({len(critical_issues)})")
            lines.append("")
            lines.append("**⚠️ IMMEDIATE ATTENTION REQUIRED**")
            lines.append("")

            for i, issue in enumerate(critical_issues, 1):
                lines.append(f"### {i}. {issue['title']}")
                lines.append(f"**Severity:** CRITICAL")

                if issue.get("location"):
                    lines.append(f"**Location:** `{issue['location']}`")

                if issue.get("cwe_id"):
                    cwe_url = f"https://cwe.mitre.org/data/definitions/{issue['cwe_id'].replace('CWE-', '')}.html"
                    lines.append(f"**CWE:** [{issue['cwe_id']}]({cwe_url})")

                lines.append("")
                lines.append(issue["description"])
                lines.append("")
                lines.append(f"**Recommendation:** {issue['recommendation']}")
                lines.append("")

        # Warnings (grouped by severity)
        warnings = result.get("warnings", [])
        if warnings:
            # Group by severity
            grouped_warnings = {"high": [], "medium": [], "low": []}
            for warning in warnings:
                severity = warning.get("severity", "low")
                if severity in grouped_warnings:
                    grouped_warnings[severity].append(warning)

            # Display each severity group
            for severity in ["high", "medium", "low"]:
                issues = grouped_warnings[severity]
                if issues:
                    style = SEVERITY_STYLES[severity]
                    lines.append(f"## {style['emoji']} {style['label']} Severity ({len(issues)})")
                    lines.append("")

                    for i, issue in enumerate(issues, 1):
                        lines.append(f"### {i}. {issue['title']}")
                        lines.append(f"**Severity:** {severity.upper()}")

                        if issue.get("location"):
                            lines.append(f"**Location:** `{issue['location']}`")

                        if issue.get("cwe_id"):
                            cwe_url = f"https://cwe.mitre.org/data/definitions/{issue['cwe_id'].replace('CWE-', '')}.html"
                            lines.append(f"**CWE:** [{issue['cwe_id']}]({cwe_url})")

                        lines.append("")
                        lines.append(issue["description"])
                        lines.append("")
                        lines.append(f"**Recommendation:** {issue['recommendation']}")
                        lines.append("")

        # Recommendations
        recommendations = result.get("recommendations", [])
        if recommendations:
            lines.append("## 💡 Recommendations")
            lines.append("")
            for rec in recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        content = "\n".join(lines)
        append_to_file(output_file, content)

        # Show success message
        console.print()
        console.print(f"[green]✓ Security analysis saved to:[/green] [cyan]{output_file}[/cyan]")
    else:
        # Display in console
        if markdown:
            display_security_result_markdown(result)
        else:
            display_security_result_rich(result)

    return result


def process_commit_range(repo, from_commit, to_commit, language, hint, output_file, exclude=None):
    """Process security analysis for a range of commits and write to file."""
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
    console.print(f"[cyan]📊 Found {total_commits} commit(s) to analyze[/cyan]")
    console.print()

    # Check credits before starting
    usage_before = check_credits_before_operation(f"security analysis of {total_commits} commit(s)")

    # Process each commit
    for idx, commit_hash in enumerate(commit_hashes, start=1):
        console.print(f"[bold cyan]▶ [{idx}/{total_commits}] Analyzing commit {commit_hash[:7]}...[/bold cyan]")

        try:
            result = process_single_commit(repo, commit_hash, language, hint, markdown=False, output_file=output_file)
            credits_charged = result.get("credits_charged", 0)
            console.print(f"[green]✓ [{idx}/{total_commits}] {commit_hash[:7]} - {credits_charged} credits charged[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to analyze commit {commit_hash[:7]}: {e}[/red]")
            console.print("[red]Stopping analysis due to error.[/red]")
            sys.exit(1)

        # Wait between requests (except for last commit)
        if idx < total_commits:
            console.print(f"[dim]⏱  Waiting {SECURITY_BATCH_DELAY} second(s)...[/dim]")
            time.sleep(SECURITY_BATCH_DELAY)
            console.print()

    console.print()
    console.print(f"[bold green]✓ Successfully analyzed {total_commits} commit(s)[/bold green]")
    console.print(f"[cyan]📁 Security report saved to: {output_file}[/cyan]")
    console.print()

    # Display total cost
    display_operation_cost(usage_before)


@click.command()
@click.option(
    "--commit", "-c",
    metavar="HASH",
    help="Single commit hash to analyze for security issues.",
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
    help="Analyze currently staged changes for security issues.",
)
@click.option(
    "--exclude", "-ex",
    metavar="HASHES",
    help="Comma-separated list of commit hashes to exclude from range (e.g., hash1,hash2,hash3).",
)
@click.option(
    "--output", "-o",
    metavar="FILE",
    help="Save security analysis to markdown file (requires --markdown).",
)
@click.option(
    "--lang",
    default=None,
    metavar="LANG",
    help="Analysis language (ISO 639-1), overrides config.",
)
@click.option(
    "--hint",
    metavar="TEXT",
    help="Additional context or specific security concerns to check (max 512 chars).",
)
@click.option(
    "--markdown", "-md",
    is_flag=True,
    help="Output as plain markdown instead of Rich panels.",
)
@validate_language
@require_git_repo
@require_api_key
def security(commit, from_commit, to_commit, staged, exclude, output, lang, hint, markdown, repo, language):
    """Perform AI-powered security analysis on commits or staged changes."""
    # Validate hint length
    if hint and len(hint) > HINT_MAX_LENGTH:
        console.print(f"[red]✗ Hint must be {HINT_MAX_LENGTH} characters or less.[/red]")
        sys.exit(1)

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
        console.print("    Analyze currently staged changes for security issues")
        console.print()
        console.print("  [cyan]--commit, -c HASH[/cyan]")
        console.print("    Analyze a single commit for security issues")
        console.print()
        console.print("  [cyan]--from HASH --to HASH[/cyan]")
        console.print("    Analyze a range of commits for security issues (both flags required)")
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
        usage_before = check_credits_before_operation("security analysis of staged changes")
        process_staged_changes(repo, language, hint, markdown, output)

        if not output:
            display_hints(markdown)

        display_operation_cost(usage_before)
    elif range_mode:
        # Commit range mode
        process_commit_range(repo, from_commit, to_commit, language, hint, output, exclude)
    else:
        # Single commit mode
        usage_before = check_credits_before_operation("security analysis")
        process_single_commit(repo, commit, language, hint, markdown, output)

        if not output:
            display_hints(markdown)

        display_operation_cost(usage_before)
