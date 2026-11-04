"""Tests for src/cohezion/governance/scripts/root_health_guard.py (2026-11-04).

The previous version of this guard existed for seven months and was run by nothing, so the
CONSUMPTION tests (is it wired into every gate, with --self-test first?) are the load-bearing
ones. See docs/audits/ROOT_CLEANUP_2026-11-04.md.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
GUARD_REL = "src/cohezion/governance/scripts/root_health_guard.py"
GUARD = REPO / GUARD_REL


def _load():
    spec = importlib.util.spec_from_file_location("root_health_guard", GUARD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rhg = _load()


def _git(repo: Path, *args: str, stdin: str | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], input=stdin, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path):
    _git(tmp_path, "init", "-q")
    blob = _git(tmp_path, "hash-object", "-w", "--stdin", stdin="x\n")
    empty = _git(tmp_path, "hash-object", "-w", "-t", "blob", "/dev/null")

    def add(path: str, *, empty_file: bool = False) -> None:
        sha = empty if empty_file else blob
        _git(tmp_path, "update-index", "--add", "--cacheinfo", f"100644,{sha},{path}")

    return tmp_path, add


# ── T1 pure helpers ───────────────────────────────────────────────────────────
def test_unlisted_root_names_only_reports_top_level():
    paths = ["docs/a.md", "satus/config.json", "README.md"]
    assert rhg.unlisted_root_names(paths, frozenset({"docs", "README.md"})) == ["satus"]


def test_case_collision_found_at_directory_level():
    groups = rhg.case_collisions(["Docs/a.md", "docs/b.md"])
    assert ["Docs", "docs"] in groups


def test_no_case_collision_for_distinct_names():
    assert rhg.case_collisions(["docs/a.md", "docs/b.md", "src/a.md"]) == []


# ── T2 behaviour against a real git index ─────────────────────────────────────
def test_clean_index_is_green(repo):
    path, add = repo
    add("README.md")
    add("docs/guide.md")
    assert rhg.scan(path, frozenset({"README.md", "docs"}), frozenset()) == []


def test_each_historical_defect_goes_red(repo):
    """The three defects the 2026-11-04 cleanup actually removed."""
    path, add = repo
    add("README.md")
    add("docs/architecture.md")
    add("docs/ARCHITECTURE.md")  # coexisted for nine months
    add("satus/config.json")  # typo directory
    add("EOF", empty_file=True)  # mistyped heredoc
    findings = rhg.scan(path, frozenset({"README.md", "docs", "EOF"}), frozenset())
    joined = "\n".join(findings)
    assert "unlisted root entry: satus" in joined
    assert "zero-byte root file: EOF" in joined
    assert "docs/ARCHITECTURE.md vs docs/architecture.md" in joined


def test_dot_names_are_not_skipped(repo):
    """The old guard skipped hidden names, so .playwright-cli/ and .claire/ walked in."""
    path, add = repo
    add(".playwright-cli/page.yml")
    assert rhg.scan(path, frozenset(), frozenset()) == [
        "unlisted root entry: .playwright-cli (add it to ROOT_ALLOWLIST in this file, or move it)"
    ]


def test_flag_files_may_be_empty(repo):
    path, add = repo
    add(".autoresearch-off", empty_file=True)
    allow = frozenset({".autoresearch-off"})
    assert rhg.scan(path, allow, frozenset({".autoresearch-off"})) == []
    assert rhg.scan(path, allow, frozenset()) != []


def test_empty_file_below_root_is_allowed(repo):
    """__init__.py and .gitkeep are legitimately empty; only the root is checked."""
    path, add = repo
    add("src/__init__.py", empty_file=True)
    assert rhg.scan(path, frozenset({"src"}), frozenset()) == []


def test_self_test_passes():
    assert rhg.self_test() == 0


# ── T3 CONSUMPTION: the invariant that matters ────────────────────────────────
@pytest.mark.parametrize(
    "gate",
    ["scripts/ci/automerge_guard.sh", ".github/workflows/ci.yml"],
)
def test_guard_is_wired_into_the_gate_with_self_test(gate):
    text = (REPO / gate).read_text(encoding="utf-8")
    assert f"{GUARD_REL} --self-test" in text, f"{gate} does not self-test the root guard"
    assert text.count(GUARD_REL) >= 2, f"{gate} self-tests the root guard but never runs the scan"


def test_guard_is_a_pre_commit_hook():
    text = (REPO / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "id: root-health-guard" in text
    assert GUARD_REL in text


def test_repo_is_currently_clean():
    assert rhg.scan(REPO) == []
