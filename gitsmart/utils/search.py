"""Search utility functions."""
from datetime import datetime

from git import GitCommandError


def get_repository_url(repo):
    """
    Get remote origin URL from repository.

    Args:
        repo: GitPython Repo instance

    Returns:
        str: Remote origin URL (first URL if multiple)

    Raises:
        ValueError: If no remote 'origin' found
    """
    try:
        # Get first URL for origin remote
        urls = list(repo.remote("origin").urls)
        if not urls:
            raise ValueError("No URL found for remote 'origin'")
        return urls[0]
    except (ValueError, AttributeError):
        raise ValueError("No git remote 'origin' found")


def collect_commits(repo, branch, anchor_hash=None, max_commits=500):
    """
    Collect commits from repository using GitPython API.

    Args:
        repo: GitPython Repo instance
        branch: Branch name to collect from
        anchor_hash: Full hash of last synced commit (None for first time)
        max_commits: Maximum number of commits to collect

    Returns:
        list[dict]: List of commit dictionaries
    """
    commits = []

    try:
        if anchor_hash is None:
            # First time - get last N commits
            commit_iter = repo.iter_commits(branch, max_count=max_commits)
        else:
            # Get commits after anchor
            # Using rev format: <anchor>..<branch> means "commits in branch but not in anchor"
            rev_range = f"{anchor_hash}..{branch}"
            try:
                commit_iter = repo.iter_commits(rev_range, max_count=max_commits)
            except GitCommandError:
                # Anchor not found in history - fallback to last N commits
                commit_iter = repo.iter_commits(branch, max_count=max_commits)

        # Collect commits
        for commit in commit_iter:
            # Parse files changed with stats
            files_changed = []
            stats = commit.stats.files  # Dict: {filepath: {'insertions': N, 'deletions': M, 'lines': K}}

            for filepath, file_stats in stats.items():
                files_changed.append({
                    "path": filepath,
                    "additions": file_stats.get("insertions", 0),
                    "deletions": file_stats.get("deletions", 0)
                })

            # Calculate total changes
            total_changes = sum(f["additions"] + f["deletions"] for f in files_changed)

            # Format date to ISO 8601
            commit_date = commit.committed_datetime.isoformat()

            # Build commit dict
            commit_dict = {
                "hash": commit.hexsha[:7],  # Short hash
                "full_hash": commit.hexsha,
                "author": commit.author.name,
                "email": commit.author.email,
                "date": commit_date,
                "message": commit.message.strip(),  # Full message (subject + body)
                "files_changed": files_changed,
                "total_changes": total_changes
            }

            commits.append(commit_dict)

    except GitCommandError as e:
        raise ValueError(f"Failed to collect commits: {e}")

    return commits


def format_commit_date(iso_date):
    """
    Format ISO datetime to YYYY-MM-DD.

    Args:
        iso_date: ISO 8601 datetime string

    Returns:
        str: Formatted date (YYYY-MM-DD)
    """
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso_date[:10]  # Fallback to first 10 chars


def format_relevance_bar(score, bar_length=20):
    """
    Format relevance score as a progress bar.

    Args:
        score: Relevance score (0.0 to 1.0)
        bar_length: Length of the bar in characters

    Returns:
        str: Formatted bar string
    """
    score_percent = int(score * 100)
    filled = int(bar_length * score)
    bar = "█" * filled + "░" * (bar_length - filled)
    return f"{bar} {score_percent}%"
