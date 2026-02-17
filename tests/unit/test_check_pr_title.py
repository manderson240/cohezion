"""Tests for scripts/ci/check_pr_title.py - conventional commit PR title validator."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "ci" / "check_pr_title.py"


def run_check(title: str) -> int:
    """Run the script with a PR title, return exit code."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), title],
        capture_output=True,
        text=True,
    )
    return result.returncode


class TestValidTitles:
    def test_feat_simple(self):
        assert run_check("feat: add auth") == 0

    def test_fix_simple(self):
        assert run_check("fix: handle null pointer") == 0

    def test_refactor_simple(self):
        assert run_check("refactor: extract helper") == 0

    def test_test_simple(self):
        assert run_check("test: add coverage for router") == 0

    def test_docs_simple(self):
        assert run_check("docs: update README") == 0

    def test_chore_simple(self):
        assert run_check("chore: bump dependencies") == 0

    def test_perf_simple(self):
        assert run_check("perf: optimize cache lookup") == 0

    def test_ci_simple(self):
        assert run_check("ci: add release workflow") == 0

    def test_build_simple(self):
        assert run_check("build: update pyproject.toml") == 0

    def test_style_simple(self):
        assert run_check("style: fix formatting") == 0

    def test_revert_simple(self):
        assert run_check("revert: undo auth changes") == 0

    def test_feat_with_scope(self):
        assert run_check("feat(api): add login endpoint") == 0

    def test_fix_with_scope(self):
        assert run_check("fix(api): handle null") == 0

    def test_breaking_change_exclamation(self):
        assert run_check("refactor!: break API") == 0

    def test_breaking_change_with_scope(self):
        assert run_check("feat(auth)!: require MFA") == 0

    def test_multi_word_description(self):
        assert run_check("feat: add conventional commit validation to CI") == 0


class TestInvalidTitles:
    def test_capitalized_no_type(self):
        assert run_check("Add auth") == 1

    def test_lowercase_past_tense(self):
        assert run_check("fixed bug") == 1

    def test_wip(self):
        assert run_check("WIP") == 1

    def test_empty_string(self):
        assert run_check("") == 1

    def test_unknown_type(self):
        assert run_check("update: something") == 1

    def test_missing_colon(self):
        assert run_check("feat add auth") == 1

    def test_missing_description(self):
        assert run_check("feat: ") == 1

    def test_type_only(self):
        assert run_check("feat:") == 1
