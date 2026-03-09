"""Tests for quality scoring engine."""

from git_forensic.detector import AIDetection
from git_forensic.scorer import (
    score_detection, score_commit_message, score_change_size,
    score_test_accompany, _is_test_file,
)


class TestIsTestFile:
    def test_test_prefix(self):
        assert _is_test_file("tests/test_detector.py")
        assert _is_test_file("test_main.py")

    def test_test_suffix(self):
        assert _is_test_file("src/auth.test.ts")
        assert _is_test_file("components/Button.spec.tsx")
        assert _is_test_file("main_test.go")

    def test_test_directory(self):
        assert _is_test_file("__tests__/App.tsx")
        assert _is_test_file("spec/models/user_spec.rb")

    def test_not_test_file(self):
        assert not _is_test_file("src/contest.ts")  # "test" substring but not a test
        assert not _is_test_file("src/latest.py")
        assert not _is_test_file("src/attestation.js")
        assert not _is_test_file("src/components/Button.tsx")


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


class TestScoreChangeSize:
    def test_initial_commit_exempt(self):
        score, reason = score_change_size(100, 50000, 0, is_initial_commit=True)
        assert score == 70.0
        assert "initial-commit" in reason
        assert "exempt" in reason

    def test_focused_change(self):
        score, _ = score_change_size(3, 50, 10)
        assert score >= 90

    def test_large_diff_penalized(self):
        score, _ = score_change_size(20, 1000, 500)
        assert score < 60


class TestScoreTestAccompany:
    def test_real_test_files_present(self):
        files = ["src/auth.ts", "tests/test_auth.py"]
        score, reason = score_test_accompany("feat: add auth", files)
        assert score == 100.0
        assert "tests-included" in reason

    def test_no_test_files_strict(self):
        files = ["src/contest.ts", "src/latest.py"]  # "test" substring but not tests
        score, reason = score_test_accompany("feat: add feature", files)
        assert score == 20.0
        assert "no-tests" in reason

    def test_docs_commit_exempt(self):
        score, _ = score_test_accompany("docs: update README", ["README.md"])
        assert score == 70.0

    def test_no_file_info_fallback(self):
        score, _ = score_test_accompany("feat: add stuff", None)
        assert score == 20.0


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
            "is_initial_commit": False,
            "file_types": {".ts": 2, ".py": 1},
        }
        defaults.update(kwargs)
        return AIDetection(**defaults)

    def test_good_commit_with_tests(self):
        d = self._make_detection(
            message="feat(auth): add OAuth2",
            files_changed=3,
            insertions=80,
            deletions=5,
        )
        score = score_detection(d, ["src/auth.ts", "src/utils.ts", "tests/auth.test.ts"])
        assert score.overall >= 75
        assert score.test_coverage == 100.0

    def test_no_tests_penalized_strictly(self):
        d = self._make_detection(message="feat: add new page")
        score = score_detection(d, ["src/page.tsx", "src/style.css"])
        assert score.test_coverage == 20.0

    def test_initial_commit_not_penalized(self):
        d = self._make_detection(
            message="feat: initial commit",
            files_changed=50,
            insertions=10000,
            deletions=0,
            is_initial_commit=True,
        )
        score = score_detection(d, ["src/main.ts"], is_initial_commit=True)
        assert score.change_size == 70.0
