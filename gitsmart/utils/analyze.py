"""Repository analysis utilities."""
from collections import defaultdict
from datetime import datetime
from pathlib import Path


EXT_TO_LANG = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".jsx": "JavaScript", ".java": "Java",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP",
    ".cs": "C#", ".cpp": "C++", ".c": "C", ".swift": "Swift",
    ".kt": "Kotlin", ".sql": "SQL", ".sh": "Shell", ".bash": "Shell",
    ".yaml": "YAML", ".yml": "YAML", ".json": "JSON", ".html": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".sass": "SCSS", ".md": "Markdown",
    ".vue": "Vue", ".svelte": "Svelte", ".dart": "Dart", ".ex": "Elixir",
    ".exs": "Elixir", ".tf": "Terraform", ".dockerfile": "Dockerfile",
}

TOP_FILES = 50


def detect_languages(repo):
    """Detect programming languages in repository."""
    try:
        files = repo.git.ls_files().splitlines()
    except Exception:
        return []
    langs = set()
    for f in files:
        ext = Path(f).suffix.lower()
        if ext in EXT_TO_LANG:
            langs.add(EXT_TO_LANG[ext])
    return sorted(langs)


def collect_git_stats(repo, since_date):
    """Parse git log and return (commits_list, total_files_count)."""
    log_raw = repo.git.log(
        f"--since={since_date}",
        "--format=GSSEP|%ae|%an|%ad",
        "--date=short",
        "--name-only",
        "--diff-filter=AM",
    )

    commits = []
    current = None
    for line in log_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("GSSEP|"):
            if current:
                commits.append(current)
            parts = line.split("|", 4)
            current = {"email": parts[1], "name": parts[2], "date": parts[3], "files": []}
        elif current is not None:
            current["files"].append(line)
    if current:
        commits.append(current)

    try:
        total_files = len(repo.git.ls_files().splitlines())
    except Exception:
        total_files = 0

    return commits, total_files


def build_analysis_payload(commits, total_files, languages, language):
    """Build API payload from collected statistics."""
    file_stats = defaultdict(lambda: {"commits": 0, "authors": set(), "last_changed": ""})
    author_commits = defaultdict(int)
    month_commits = defaultdict(int)

    for commit in commits:
        name = commit["name"] or commit["email"]
        date = commit["date"]
        month = date[:7]

        author_commits[name] += 1
        month_commits[month] += 1

        for f in commit["files"]:
            file_stats[f]["commits"] += 1
            file_stats[f]["authors"].add(name)
            if not file_stats[f]["last_changed"] or date > file_stats[f]["last_changed"]:
                file_stats[f]["last_changed"] = date

    top_files = sorted(file_stats.items(), key=lambda x: x[1]["commits"], reverse=True)[:TOP_FILES]
    files_list = [
        {
            "file": f,
            "commits": s["commits"],
            "authors": sorted(s["authors"]),
            "last_changed": s["last_changed"],
        }
        for f, s in top_files
    ]

    total = sum(author_commits.values()) or 1
    contributors = sorted(
        [
            {"author": name, "commits": count, "percent": round(count / total * 100, 1)}
            for name, count in author_commits.items()
        ],
        key=lambda x: x["commits"],
        reverse=True,
    )

    commits_per_month = [
        {"month": m, "commits": c} for m, c in sorted(month_commits.items())
    ]

    period_from = min(c["date"] for c in commits) if commits else datetime.now().strftime("%Y-%m-%d")
    period_to = max(c["date"] for c in commits) if commits else datetime.now().strftime("%Y-%m-%d")

    return {
        "total_commits": len(commits),
        "total_files": total_files,
        "period_from": period_from,
        "period_to": period_to,
        "languages": languages,
        "files": files_list,
        "contributors": contributors,
        "commits_per_month": commits_per_month,
        "language": language,
    }


def display_analysis(result, payload):
    """Display analysis results."""
    from rich.console import Console
    console = Console()

    separator = "[green]─────────────────────────────────────[/green]"
    period = f"{payload['period_from']} – {payload['period_to']}"

    console.print()
    console.print("[bold cyan]📈 Repository Analytics[/bold cyan]")
    console.print(separator)
    console.print(
        f"[white]📊 Overview: {payload['total_commits']} commits,"
        f" {payload['total_files']} files · {period}[/white]"
    )

    hotspots = result.get("hotspots") or []
    if hotspots:
        console.print(f"\n[bold white]🔥 Hotspots:[/bold white]")
        for h in hotspots:
            console.print(f"[yellow]- {h['file']}:[/yellow] [white]{h['reason']}[/white]")

    insights = result.get("insights") or []
    if insights:
        console.print(f"\n[bold white]💡 Insights:[/bold white]")
        for i in insights:
            console.print(f"[white]- {i}[/white]")

    contributors = result.get("contributors_analysis") or []
    if contributors:
        console.print(f"\n[bold white]👥 Contributors:[/bold white]")
        for c in contributors:
            console.print(f"[cyan]- {c['author']}:[/cyan] [white]{c['insight']}[/white]")

    recommendations = result.get("recommendations") or []
    if recommendations:
        console.print(f"\n[bold white]🔧 Recommendations:[/bold white]")
        for r in recommendations:
            console.print(f"[white]- {r}[/white]")

    console.print(f"\n{separator}\n")
