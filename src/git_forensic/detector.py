"""AI commit detection engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from git import Commit

# Patterns that indicate AI authorship (scored by confidence)
AI_SIGNATURES: list[tuple[str, float, str]] = [
    # (pattern, confidence, source_label)
    (r"Co-Authored-By:\s*Claude", 0.95, "Claude Co-Author"),
    (r"Co-Authored-By:\s*GitHub Copilot", 0.95, "Copilot Co-Author"),
    (r"Co-Authored-By:\s*Cursor", 0.90, "Cursor Co-Author"),
    (r"Co-Authored-By:\s*ChatGPT", 0.90, "ChatGPT Co-Author"),
    (r"Co-Authored-By:\s*Gemini", 0.90, "Gemini Co-Author"),
    (r"Generated (by|with|using) (Claude|GPT|Copilot|AI|Cursor|Gemini)", 0.85, "Generated-by tag"),
    (r"🤖\s*(Generated|Created|Built)", 0.80, "Robot emoji tag"),
    (r"aider:", 0.90, "Aider prefix"),
]

# Heuristic patterns in commit messages (lower confidence)
HEURISTIC_PATTERNS: list[tuple[str, float, str]] = [
    (r"^(feat|fix|refactor|docs|test|chore|perf|ci)(\(.+\))?:\s", 0.15, "Conventional commit"),
    (r"(추가|수정|개선|제거|변경)\s*[—–-]\s*", 0.10, "Structured Korean desc"),
]


@dataclass
class AIDetection:
    commit_hash: str
    short_hash: str
    author: str
    date: str
    message: str
    confidence: float
    signals: list[str] = field(default_factory=list)
    ai_model: str = "unknown"
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0

    @property
    def is_ai(self) -> bool:
        return self.confidence >= 0.5

    @property
    def confidence_label(self) -> str:
        if self.confidence >= 0.9:
            return "confirmed"
        if self.confidence >= 0.7:
            return "high"
        if self.confidence >= 0.5:
            return "medium"
        return "low"


def extract_ai_model(text: str) -> str:
    """Extract specific AI model name from commit text."""
    patterns = [
        (r"Claude\s*(Opus|Sonnet|Haiku)\s*[\d.]+", lambda m: f"Claude {m.group(1)}"),
        (r"Claude\s*(Opus|Sonnet|Haiku)", lambda m: f"Claude {m.group(1)}"),
        (r"Claude", lambda _: "Claude"),
        (r"GPT-?4[o]?", lambda _: "GPT-4"),
        (r"ChatGPT", lambda _: "ChatGPT"),
        (r"Copilot", lambda _: "Copilot"),
        (r"Cursor", lambda _: "Cursor"),
        (r"Gemini", lambda _: "Gemini"),
        (r"aider", lambda _: "Aider"),
    ]
    for pattern, extractor in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return extractor(match)
    return "unknown"


def detect_commit(commit: Commit) -> AIDetection:
    """Analyze a single commit for AI authorship signals."""
    message = commit.message or ""
    full_text = message
    signals: list[str] = []
    max_confidence = 0.0

    # Check explicit AI signatures
    for pattern, confidence, label in AI_SIGNATURES:
        if re.search(pattern, full_text, re.IGNORECASE):
            signals.append(label)
            max_confidence = max(max_confidence, confidence)

    # Check heuristic patterns (additive, capped)
    heuristic_score = 0.0
    for pattern, confidence, label in HEURISTIC_PATTERNS:
        if re.search(pattern, full_text, re.IGNORECASE):
            heuristic_score += confidence

    if not signals:
        max_confidence = min(heuristic_score, 0.40)
        if heuristic_score > 0:
            signals.append("heuristic-only")

    # Extract stats
    try:
        stats = commit.stats.total
        files_changed = stats.get("files", 0)
        insertions = stats.get("insertions", 0)
        deletions = stats.get("deletions", 0)
    except Exception:
        files_changed = insertions = deletions = 0

    return AIDetection(
        commit_hash=commit.hexsha,
        short_hash=commit.hexsha[:7],
        author=str(commit.author),
        date=commit.authored_datetime.strftime("%Y-%m-%d"),
        message=message.split("\n")[0][:80],
        confidence=max_confidence,
        signals=signals,
        ai_model=extract_ai_model(full_text),
        files_changed=files_changed,
        insertions=insertions,
        deletions=deletions,
    )


def scan_repository(
    repo_path: str,
    since: str | None = None,
    branch: str | None = None,
    min_confidence: float = 0.5,
) -> list[AIDetection]:
    """Scan all commits in a repository for AI authorship."""
    from git import Repo

    repo = Repo(repo_path)
    kwargs: dict = {"all": branch is None}
    if branch:
        kwargs["rev"] = branch
    if since:
        kwargs["after"] = since

    detections: list[AIDetection] = []
    for commit in repo.iter_commits(**kwargs):
        detection = detect_commit(commit)
        if detection.confidence >= min_confidence:
            detections.append(detection)

    return sorted(detections, key=lambda d: d.date, reverse=True)
