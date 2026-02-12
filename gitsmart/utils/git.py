"""Git utility functions."""
import re


def parse_name_status(raw):
    """Parse git diff --name-status output into list of (status, path)."""
    result = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 2)
        status = parts[0][0]  # first char: A, M, D, R, etc.
        path = parts[-1]      # last part is always the target path
        result.append((status, path))
    return result


def parse_shortstat(shortstat):
    """Parse git diff --shortstat output into (files, added, removed)."""
    files = added = removed = None
    m = re.search(r"(\d+) files? changed", shortstat)
    if m:
        files = int(m.group(1))
    m = re.search(r"(\d+) insertion", shortstat)
    if m:
        added = int(m.group(1))
    m = re.search(r"(\d+) deletion", shortstat)
    if m:
        removed = int(m.group(1))
    return files, added, removed


def detect_base_branch(repo):
    """Detect main/master branch in repository."""
    branches = {b.name for b in repo.branches}
    if "main" in branches:
        return "main"
    if "master" in branches:
        return "master"
    return None


def get_staged_diff(repo, max_chars=None):
    """Get staged diff, optionally truncated."""
    diff = repo.git.diff("--staged")
    if max_chars and len(diff) > max_chars:
        return diff[:max_chars], True
    return diff, False


def get_commit_data(repo, commit_hash):
    """
    Get detailed commit data for explain endpoint.

    Returns dict with:
    - hash: short hash (7 chars)
    - full_hash: full 40-char hash
    - author: author name
    - email: author email
    - date: ISO 8601 date with timezone
    - message: full commit message
    - files_changed: list of {path, additions, deletions}
    - total_changes: total lines changed
    - diff: full git diff
    """
    try:
        commit = repo.commit(commit_hash)
    except Exception:
        return None

    # Basic commit info
    data = {
        "hash": commit.hexsha[:7],
        "full_hash": commit.hexsha,
        "author": commit.author.name,
        "email": commit.author.email,
        "date": commit.committed_datetime.isoformat(),
        "message": commit.message.strip(),
    }

    # Get diff and files changed
    if commit.parents:
        parent = commit.parents[0]
        diff_output = repo.git.diff(parent.hexsha, commit.hexsha)

        # Parse numstat for file statistics
        numstat = repo.git.diff(parent.hexsha, commit.hexsha, numstat=True)
        files_changed = []
        total_changes = 0

        for line in numstat.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                additions = int(parts[0]) if parts[0] != "-" else 0
                deletions = int(parts[1]) if parts[1] != "-" else 0
                path = parts[2]
                files_changed.append({
                    "path": path,
                    "additions": additions,
                    "deletions": deletions,
                })
                total_changes += additions + deletions
    else:
        # Initial commit (no parents)
        diff_output = repo.git.show(commit.hexsha, format="", patch=True)
        numstat = repo.git.show(commit.hexsha, format="", numstat=True)
        files_changed = []
        total_changes = 0

        for line in numstat.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                additions = int(parts[0]) if parts[0] != "-" else 0
                deletions = int(parts[1]) if parts[1] != "-" else 0
                path = parts[2]
                files_changed.append({
                    "path": path,
                    "additions": additions,
                    "deletions": deletions,
                })
                total_changes += additions + deletions

    data["files_changed"] = files_changed
    data["total_changes"] = total_changes
    data["diff"] = diff_output

    return data


def get_commits_in_range(repo, from_commit, to_commit):
    """
    Get list of commit hashes in range from_commit..to_commit (inclusive).

    Returns list of commit hashes in chronological order (oldest to newest).
    Validates that both commits exist.
    Includes both from_commit and to_commit in the result.

    Returns None if commits are invalid.
    """
    try:
        # Validate commits exist
        from_obj = repo.commit(from_commit)
        to_obj = repo.commit(to_commit)

        # Get commits in range (from_commit..to_commit) inclusive
        # Use from_commit^..to_commit to include from_commit itself
        # Handle case where from_commit is the initial commit (no parent)
        try:
            range_spec = f"{from_commit}^..{to_commit}"
            commits_output = repo.git.log(
                range_spec,
                format="%H",
                reverse=True  # Chronological order (oldest first)
            )
        except Exception:
            # from_commit might be the initial commit (no parent)
            # Get all commits up to to_commit and filter from from_commit onwards
            all_commits_output = repo.git.log(
                to_commit,
                format="%H",
                reverse=True
            )

            if not all_commits_output.strip():
                return []

            all_commits = all_commits_output.strip().split("\n")

            # Find from_commit in the list and slice from there
            try:
                from_idx = all_commits.index(from_obj.hexsha)
                return all_commits[from_idx:]
            except ValueError:
                # from_commit not found in ancestry of to_commit
                return []

        if not commits_output.strip():
            return []

        return commits_output.strip().split("\n")
    except Exception:
        return None


def get_staged_data(repo):
    """
    Get detailed data for staged changes (similar to get_commit_data but for staged files).

    Returns dict with:
    - files_changed: list of {path, additions, deletions}
    - total_changes: total lines changed
    - diff: full git diff of staged files

    Returns None if no staged changes found.
    """
    try:
        # Check if there are staged changes
        staged_diff = repo.git.diff("--staged")
        if not staged_diff.strip():
            return None

        # Parse numstat for file statistics
        numstat = repo.git.diff("--staged", numstat=True)
        files_changed = []
        total_changes = 0

        for line in numstat.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                additions = int(parts[0]) if parts[0] != "-" else 0
                deletions = int(parts[1]) if parts[1] != "-" else 0
                path = parts[2]
                files_changed.append({
                    "path": path,
                    "additions": additions,
                    "deletions": deletions,
                })
                total_changes += additions + deletions

        return {
            "files_changed": files_changed,
            "total_changes": total_changes,
            "diff": staged_diff,
        }
    except Exception:
        return None


def get_current_branch_name(repo):
    """
    Get current branch name, handling detached HEAD.

    Returns branch name or None if detached HEAD.
    """
    try:
        return repo.active_branch.name
    except TypeError:
        return None
