"""Tests for quality scoring engine."""

from git_forensic.detector import AIDetection
from git_forensic.scorer import score_detection, score_commit_message


class TestScoreCommitMessage:
    def test_conventional_commit_good(self):
        score, _ = score_commit_message("feat(auth): add OAuth2 login flow")
        assert score >= 80

    def test_short_message_penalized(self):
        score, _ = score_commit_message("fix")
        assert score < 50

    def test_too_long_penalized(self):
        score, _ = score_commit_message("x" * 100)
        assert score < 70


class TestScoreDetection:
    def _make_detection(self, **kwargs) -> AIDetection:
        defaults = {
            "commit_hash": "abc1234",
            "short_hash": "abc1234",
            "author": "dev",
            "date": "2026-03-01",
            "message": "feat: add feature",
            "confidence": 0.95,
            "signals": ["Claude Co-Author"],
            "ai_model": "Claude Opus",
            "files_changed": 3,
            "insertions": 50,
            "deletions": 10,
        }
        defaults.update(kwargs)
        return AIDetection(**defaults)

    def test_good_commit_high_score(self):
        d = self._make_detection(
            message="feat(auth): add OAuth2 — 테스트 포함",
            files_changed=2,
            insertions=40,
            deletions=5,
        )
        score = score_detection(d, ["src/auth.ts", "tests/auth.test.ts"])
        assert score.overall >= 70
        assert score.grade in ("A+", "A", "B")

    def test_large_diff_penalized(self):
        d = self._make_detection(
            message="refactor: massive rewrite",
            files_changed=25,
            insertions=1500,
            deletions=800,
        )
        score = score_detection(d)
        assert score.change_size < 60

    def test_no_tests_penalized(self):
        d = self._make_detection(message="feat: add new page")
        score = score_detection(d, ["src/page.tsx"])
        assert score.test_coverage < 50
