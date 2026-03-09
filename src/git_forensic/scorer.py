"""Quality scoring engine for AI-authored commits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from git_forensic.detector import AIDetection


@dataclass
class QualityScore:
    overall: float  # 0-100
    commit_message: float
    change_size: float
    test_coverage: float
    doc_coverage: float
    breakdown: dict[str, str]

    @property
    def grade(self) -> str:
        if self.overall >= 90:
            return "A+"
        if self.overall >= 80:
            return "A"
        if self.overall >= 70:
            return "B"
        if self.overall >= 60:
            return "C"
        if self.overall >= 50:
            return "D"
        return "F"

    @property
    def grade_color(self) -> str:
        colors = {"A+": "green", "A": "green", "B": "yellow", "C": "yellow", "D": "red", "F": "red"}
        return colors.get(self.grade, "white")


def score_commit_message(message: str) -> tuple[float, str]:
    """Score commit message quality (0-100)."""
    score = 50.0
    reasons = []

    # Conventional commit format
    import re
    if re.match(r"^(feat|fix|refactor|docs|test|chore|perf|ci)(\(.+\))?:\s", message):
        score += 20
        reasons.append("conventional-commit")

    # Length check
    first_line = message.split("\n")[0]
    if 10 <= len(first_line) <= 72:
        score += 15
        reasons.append("good-length")
    elif len(first_line) > 72:
        score -= 10
        reasons.append("too-long")
    elif len(first_line) < 10:
        score -= 20
        reasons.append("too-short")

    # Descriptive (not just "fix" or "update")
    if len(first_line.split()) >= 3:
        score += 15
        reasons.append("descriptive")

    return min(100, max(0, score)), ", ".join(reasons)


def score_change_size(files_changed: int, insertions: int, deletions: int) -> tuple[float, str]:
    """Score based on change granularity (smaller = better)."""
    total_lines = insertions + deletions

    if total_lines == 0:
        return 50.0, "no-changes"

    # Ideal: focused changes (< 200 lines, < 10 files)
    score = 100.0
    reasons = []

    if total_lines > 500:
        score -= 30
        reasons.append(f"large-diff({total_lines}L)")
    elif total_lines > 200:
        score -= 15
        reasons.append(f"medium-diff({total_lines}L)")
    else:
        reasons.append(f"focused({total_lines}L)")

    if files_changed > 15:
        score -= 25
        reasons.append(f"many-files({files_changed})")
    elif files_changed > 8:
        score -= 10
        reasons.append(f"several-files({files_changed})")
    else:
        reasons.append(f"few-files({files_changed})")

    return max(0, score), ", ".join(reasons)


def score_test_accompany(message: str, files_changed_names: list[str] | None = None) -> tuple[float, str]:
    """Score whether the commit includes test changes."""
    msg_lower = message.lower()
    has_test_mention = any(kw in msg_lower for kw in ["test", "spec", "테스트", "검증"])

    if files_changed_names:
        has_test_files = any(
            "test" in f.lower() or "spec" in f.lower() or "__tests__" in f
            for f in files_changed_names
        )
    else:
        has_test_files = has_test_mention

    if has_test_files:
        return 100.0, "tests-included"
    if msg_lower.startswith("docs:") or msg_lower.startswith("ci:") or msg_lower.startswith("chore:"):
        return 70.0, "docs/ci(tests-optional)"
    return 30.0, "no-tests"


def score_doc_coverage(message: str) -> tuple[float, str]:
    """Score documentation effort."""
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in ["docs:", "문서", "readme", "jsdoc", "docstring"]):
        return 100.0, "docs-commit"
    if "—" in message or ":" in message:
        return 70.0, "self-documenting-msg"
    return 40.0, "minimal-docs"


def score_detection(detection: AIDetection, file_names: list[str] | None = None) -> QualityScore:
    """Calculate comprehensive quality score for an AI detection."""
    msg_score, msg_reason = score_commit_message(detection.message)
    size_score, size_reason = score_change_size(
        detection.files_changed, detection.insertions, detection.deletions
    )
    test_score, test_reason = score_test_accompany(detection.message, file_names)
    doc_score, doc_reason = score_doc_coverage(detection.message)

    # Weighted average
    overall = (
        msg_score * 0.25
        + size_score * 0.30
        + test_score * 0.30
        + doc_score * 0.15
    )

    return QualityScore(
        overall=round(overall, 1),
        commit_message=msg_score,
        change_size=size_score,
        test_coverage=test_score,
        doc_coverage=doc_score,
        breakdown={
            "commit_message": msg_reason,
            "change_size": size_reason,
            "test_coverage": test_reason,
            "doc_coverage": doc_reason,
        },
    )
