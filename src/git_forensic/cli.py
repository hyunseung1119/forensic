"""CLI entry point for git-forensic."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import click
from rich.console import Console

# Fix Windows cp949 encoding — force UTF-8 stdout
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from git_forensic.detector import scan_repository
from git_forensic.reporter import (
    export_json,
    render_commits_table,
    render_quality_breakdown,
    render_summary,
)
from git_forensic.scorer import score_detection


@click.command()
@click.argument("repo_path", default=".", type=click.Path(exists=True))
@click.option("--since", "-s", help="Only scan commits after this date (YYYY-MM-DD)")
@click.option("--branch", "-b", help="Scan specific branch (default: all)")
@click.option("--min-confidence", "-c", default=0.5, help="Minimum confidence threshold (0-1)")
@click.option("--limit", "-n", default=30, help="Max commits to display")
@click.option("--json-out", "-o", help="Export results to JSON file")
@click.option("--html", "-h", "html_out", help="Export HTML dashboard report")
@click.option("--open", "auto_open", is_flag=True, help="Auto-open HTML report in browser")
@click.option("--all-commits", is_flag=True, help="Show all commits including low confidence")
def main(
    repo_path: str,
    since: str | None,
    branch: str | None,
    min_confidence: float,
    limit: int,
    json_out: str | None,
    html_out: str | None,
    auto_open: bool,
    all_commits: bool,
) -> None:
    """Audit AI-authored code quality in git repositories.

    Scans commit history for AI authorship signals (Co-Authored-By, etc.)
    and scores code quality across multiple dimensions.

    \b
    Examples:
        git-forensic .                          # Scan current repo
        git-forensic /path/to/repo              # Scan specific repo
        git-forensic . --since 2026-01          # Only recent commits
        git-forensic . -o report.json           # Export JSON report
        git-forensic . -h report.html --open    # HTML dashboard + open
    """
    console = Console(force_terminal=True)

    if all_commits:
        min_confidence = 0.0

    repo = Path(repo_path).resolve()
    if not (repo / ".git").exists():
        console.print(f"[red]Error:[/red] {repo} is not a git repository")
        sys.exit(1)

    console.print(f"\n[dim]Scanning {repo}...[/dim]\n")

    # Count total commits
    from git import Repo
    git_repo = Repo(str(repo))
    total_commits = sum(1 for _ in git_repo.iter_commits(all=True))

    # Detect AI commits
    detections = scan_repository(
        str(repo),
        since=since,
        branch=branch,
        min_confidence=min_confidence,
    )

    if not detections:
        console.print("[yellow]No AI-authored commits found.[/yellow]")
        console.print("[dim]Try --all-commits to see heuristic matches.[/dim]")
        return

    # Score each detection
    scores = []
    for detection in detections:
        try:
            commit = git_repo.commit(detection.commit_hash)
            file_names = list(commit.stats.files.keys())
        except Exception:
            file_names = None
        scores.append(score_detection(detection, file_names))

    # Render reports
    render_summary(detections, scores, total_commits, console)
    console.print()
    render_commits_table(detections, scores, console, limit)
    console.print()
    render_quality_breakdown(scores, console)

    # JSON export
    if json_out:
        export_json(detections, scores, total_commits, json_out)
        console.print(f"\n[green]✓[/green] JSON report exported to {json_out}")

    # HTML export
    if html_out:
        from git_forensic.html_report import export_html
        repo_name = repo.name
        export_html(detections, scores, total_commits, html_out, repo_name)
        console.print(f"[green]✓[/green] HTML dashboard exported to {html_out}")
        if auto_open:
            import webbrowser
            webbrowser.open(str(Path(html_out).resolve()))

    console.print()


if __name__ == "__main__":
    main()
