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
