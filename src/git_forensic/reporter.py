"""Rich-based terminal report generator."""

from __future__ import annotations

import json
from collections import Counter
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from git_forensic.detector import AIDetection
    from git_forensic.scorer import QualityScore


def render_summary(
    detections: list[AIDetection],
    scores: list[QualityScore],
    total_commits: int,
    console: Console | None = None,
) -> None:
    """Render the main summary panel."""
    console = console or Console()
    ai_count = len(detections)
    ai_ratio = (ai_count / total_commits * 100) if total_commits else 0
    avg_score = sum(s.overall for s in scores) / len(scores) if scores else 0
    avg_grade = _avg_grade(avg_score)

    total_insertions = sum(d.insertions for d in detections)
    total_deletions = sum(d.deletions for d in detections)

    # Model distribution
    model_counts = Counter(d.ai_model for d in detections)
    model_str = " | ".join(f"{m}: {c}" for m, c in model_counts.most_common(5))

    # Confidence distribution
    confirmed = sum(1 for d in detections if d.is_confirmed)
    high = sum(1 for d in detections if 0.7 <= d.confidence < 0.9 and not d.is_confirmed)
    medium = sum(1 for d in detections if 0.5 <= d.confidence < 0.7)
    heuristic = sum(1 for d in detections if d.confidence < 0.5)

    summary = Text()
    summary.append("📊 Repository AI Audit Summary\n\n", style="bold cyan")
    summary.append(f"  Total Commits:    {total_commits}\n")
    summary.append(f"  AI Commits:       {ai_count} ({ai_ratio:.1f}%)\n", style="bold")
    summary.append(f"  AI Lines Added:   +{total_insertions:,}\n", style="green")
    summary.append(f"  AI Lines Removed: -{total_deletions:,}\n", style="red")
    summary.append(f"\n  Quality Grade:    {avg_grade} ({avg_score:.1f}/100)\n", style=f"bold {_grade_color(avg_grade)}")
    summary.append(f"\n  Models:           {model_str}\n")
    conf_parts = [f"✅ {confirmed} confirmed"]
    if high: conf_parts.append(f"🔶 {high} high")
    if medium: conf_parts.append(f"🔸 {medium} medium")
    if heuristic: conf_parts.append(f"⚪ {heuristic} heuristic")
    summary.append(f"  Confidence:       {' | '.join(conf_parts)}\n")

    console.print(Panel(summary, title="[bold]🔍 git-forensic[/bold]", border_style="blue"))


def render_commits_table(
    detections: list[AIDetection],
    scores: list[QualityScore],
    console: Console | None = None,
    limit: int = 20,
) -> None:
    """Render detailed commits table."""
    console = console or Console()

    table = Table(title=f"AI-Authored Commits (top {min(limit, len(detections))})", show_lines=False)
    table.add_column("Date", style="dim", width=10)
    table.add_column("Hash", style="cyan", width=7)
    table.add_column("Model", style="magenta", width=14)
    table.add_column("Message", width=45)
    table.add_column("Grade", justify="center", width=5)
    table.add_column("Score", justify="right", width=5)
    table.add_column("Confidence", justify="center", width=10)

    for detection, score in zip(detections[:limit], scores[:limit]):
        conf_icon = "✅" if detection.confidence >= 0.9 else ("🔶" if detection.confidence >= 0.7 else "🔸")
        table.add_row(
            detection.date,
            detection.short_hash,
            detection.ai_model,
            detection.message[:45],
            Text(score.grade, style=f"bold {score.grade_color}"),
            f"{score.overall:.0f}",
            f"{conf_icon} {detection.confidence:.0%}",
        )

    console.print(table)


def render_quality_breakdown(
    scores: list[QualityScore],
    console: Console | None = None,
) -> None:
    """Render quality dimension breakdown."""
    console = console or Console()
    if not scores:
        return

    avg_msg = sum(s.commit_message for s in scores) / len(scores)
    avg_size = sum(s.change_size for s in scores) / len(scores)
    avg_test = sum(s.test_coverage for s in scores) / len(scores)
    avg_doc = sum(s.doc_coverage for s in scores) / len(scores)

    table = Table(title="Quality Breakdown (averages)", show_lines=False)
    table.add_column("Dimension", width=20)
    table.add_column("Score", justify="right", width=8)
    table.add_column("Bar", width=30)
    table.add_column("Weight", justify="right", width=8)

    for name, avg, weight in [
        ("Commit Message", avg_msg, "25%"),
        ("Change Size", avg_size, "30%"),
        ("Test Coverage", avg_test, "30%"),
        ("Documentation", avg_doc, "15%"),
    ]:
        bar = _bar(avg)
        color = "green" if avg >= 70 else ("yellow" if avg >= 50 else "red")
        table.add_row(name, f"[{color}]{avg:.1f}[/{color}]", bar, weight)

    console.print(table)


def export_json(
    detections: list[AIDetection],
    scores: list[QualityScore],
    total_commits: int,
    output_path: str,
) -> None:
    """Export results as JSON."""
    data = {
        "summary": {
            "total_commits": total_commits,
            "ai_commits": len(detections),
            "ai_ratio": round(len(detections) / total_commits * 100, 1) if total_commits else 0,
            "avg_score": round(sum(s.overall for s in scores) / len(scores), 1) if scores else 0,
        },
        "commits": [
            {
                "hash": d.commit_hash,
                "date": d.date,
                "author": d.author,
                "message": d.message,
                "ai_model": d.ai_model,
                "confidence": d.confidence,
                "signals": d.signals,
                "score": {
                    "overall": s.overall,
                    "grade": s.grade,
                    "commit_message": s.commit_message,
                    "change_size": s.change_size,
                    "test_coverage": s.test_coverage,
                    "doc_coverage": s.doc_coverage,
                },
                "stats": {
                    "files_changed": d.files_changed,
                    "insertions": d.insertions,
                    "deletions": d.deletions,
                },
            }
            for d, s in zip(detections, scores)
        ],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _bar(value: float, width: int = 25) -> str:
    filled = int(value / 100 * width)
    color = "green" if value >= 70 else ("yellow" if value >= 50 else "red")
    return f"[{color}]{'█' * filled}{'░' * (width - filled)}[/{color}] "


def _avg_grade(score: float) -> str:
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"


def _grade_color(grade: str) -> str:
    return {"A+": "green", "A": "green", "B": "yellow", "C": "yellow", "D": "red", "F": "red"}.get(grade, "white")
