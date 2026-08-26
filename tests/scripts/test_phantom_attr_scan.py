"""Tests for scripts/ci/phantom_attr_scan.py (2026-08-26).

Structural-before-behavioral, per verification-depth.md. The CONSUMPTION tests
are the load-bearing ones: a scanner that exists but is not wired into a gate is
dormant, and dormancy is exactly the failure class it was built to catch.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
SCANNER = REPO / "scripts" / "ci" / "phantom_attr_scan.py"


def _load():
    spec = importlib.util.spec_from_file_location("phantom_attr_scan", SCANNER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pas = _load()


def _tree(tmp_path: Path, body: str) -> Path:
    (tmp_path / "mod").mkdir(exist_ok=True)
    (tmp_path / "mod" / "m.py").write_text(body, encoding="utf-8")
    return tmp_path


_CLASS = "class R:\n    success: bool\n    metrics: dict\n\n    def method(self):\n        self.bound = 1\n"


# ── T1 structural ─────────────────────────────────────────────────────────────
def test_t1_scanner_exists_and_registry_is_populated():
    assert SCANNER.exists()
    assert pas.REGISTRY, "an empty registry makes the gate structurally unable to fail"
    for entry in pas.REGISTRY:
        assert len(entry) == 4, f"registry entry must be a 4-tuple, got {entry!r}"


def test_t1_self_test_passes():
    assert pas.self_test() == 0


# ── T2 discriminating ─────────────────────────────────────────────────────────
def test_t2_flags_attribute_the_class_does_not_define(tmp_path):
    root = _tree(tmp_path, _CLASS + '\n\ndef c(result):\n    return getattr(result, "error", "")\n')
    failures = pas.scan([("mod/m.py", "result", "mod/m.py", "R")], root=root)
    assert len(failures) == 1
    assert "'error'" in failures[0]


@pytest.mark.parametrize("attr", ["success", "metrics", "method", "bound"])
def test_t2_passes_real_attributes(tmp_path, attr):
    """Fields, methods, and self-bound attrs must all count as present."""
    root = _tree(
        tmp_path, _CLASS + f'\n\ndef c(result):\n    return getattr(result, "{attr}", None)\n'
    )
    assert pas.scan([("mod/m.py", "result", "mod/m.py", "R")], root=root) == []


# ── T2 negative controls — a false-positive-prone gate gets ignored ───────────
def test_t2_dynamic_attribute_name_is_never_flagged(tmp_path):
    """getattr(x, name, ...) is unresolvable; flagging it would be noise, not signal."""
    body = (
        _CLASS
        + '\n\ndef c(result):\n    for name in ("output", "error"):\n        v = getattr(result, name, "")\n    return v\n'
    )
    root = _tree(tmp_path, body)
    assert pas.scan([("mod/m.py", "result", "mod/m.py", "R")], root=root) == []


def test_t2_other_variables_are_not_flagged(tmp_path):
    """Only the registered variable is inspected — an unrelated object is out of scope.

    The fixture must ALSO bind `result` validly: a file with no `result` at all is a
    stale registry entry, not a scoping test (caught when the staleness guard landed).
    """
    body = (
        _CLASS + "\n\ndef c(result, other):\n"
        '    a = getattr(result, "metrics", None)\n'
        '    b = getattr(other, "error", "")\n'
        "    return a, b\n"
    )
    root = _tree(tmp_path, body)
    assert pas.scan([("mod/m.py", "result", "mod/m.py", "R")], root=root) == []


def test_t2_missing_class_reports_rather_than_passing_silently(tmp_path):
    """'Cannot verify' must NOT read as 'verified clean' — the whole point of the gate."""
    root = _tree(tmp_path, 'def c(result):\n    return getattr(result, "error", "")\n')
    failures = pas.scan([("mod/m.py", "result", "mod/m.py", "Absent")], root=root)
    assert failures and "cannot verify" in failures[0]


# ── T3 CONSUMPTION — the invariant that matters ───────────────────────────────
@pytest.mark.parametrize(
    "gate",
    ["scripts/ci/automerge_guard.sh", ".github/workflows/ci.yml"],
)
def test_t3_scanner_is_wired_into_the_gate(gate):
    """A scanner with no gate calling it is dormant — the class it exists to catch."""
    text = (REPO / gate).read_text(encoding="utf-8")
    assert "phantom_attr_scan.py" in text, f"{gate} does not run the scanner"
    assert "phantom_attr_scan.py --self-test" in text, (
        f"{gate} runs the scanner without --self-test; an unverified scanner's "
        "green is not evidence"
    )


def test_t3_repo_is_currently_clean():
    """The real registry against the real tree."""
    assert pas.scan(pas.REGISTRY) == []


# ── T2 staleness guard — found by attacking the scanner's own design ──────────
def test_t2_renamed_variable_reports_stale_instead_of_silently_passing(tmp_path):
    """The registry binds by variable NAME. A rename must not silently lose coverage.

    Without this guard the scanner reports GREEN after a rename — the same
    can't-report-its-own-failure class it was built to detect.
    """
    root = _tree(tmp_path, _CLASS + '\n\ndef c(res):\n    return getattr(res, "error", "")\n')
    failures = pas.scan([("mod/m.py", "result", "mod/m.py", "R")], root=root)
    assert failures, "renamed variable silently passed — coverage lost with no signal"
    assert "STALE REGISTRY" in failures[0]


def test_t2_present_variable_does_not_trip_the_staleness_guard(tmp_path):
    """Negative control: the guard must not fire when the variable IS present."""
    root = _tree(
        tmp_path, _CLASS + '\n\ndef c(result):\n    return getattr(result, "metrics", None)\n'
    )
    assert pas.scan([("mod/m.py", "result", "mod/m.py", "R")], root=root) == []


# ── T2 false-positive regressions (adversarial seam attack, 2026-08-26) ───────
# A scanner that cries wolf gets ignored, so a false positive costs more than a
# missed check. Both of these WERE false positives before the seam attack.
def test_t2_class_with_dunder_getattr_is_never_flagged(tmp_path):
    """A class defining __getattr__ accepts ANY attribute by contract."""
    body = (
        "class R:\n    success: bool\n\n    def __getattr__(self, n):\n        return None\n"
        '\n\ndef c(result):\n    return getattr(result, "anything", "")\n'
    )
    root = _tree(tmp_path, body)
    assert pas.scan([("mod/m.py", "result", "mod/m.py", "R")], root=root) == []


def test_t2_attribute_inherited_from_a_local_base_is_not_flagged(tmp_path):
    """Inherited fields count — flagging them would fire on every subclass."""
    body = (
        "class Base:\n    error: str\n\n\nclass R(Base):\n    success: bool\n"
        '\n\ndef c(result):\n    return getattr(result, "error", "")\n'
    )
    root = _tree(tmp_path, body)
    assert pas.scan([("mod/m.py", "result", "mod/m.py", "R")], root=root) == []


def test_t2_unresolvable_base_reports_cannot_verify_not_clean(tmp_path):
    """An imported base makes the field set unknowable — say so, never imply clean."""
    body = (
        "from x import Base\n\n\nclass R(Base):\n    success: bool\n"
        '\n\ndef c(result):\n    return getattr(result, "error", "")\n'
    )
    root = _tree(tmp_path, body)
    failures = pas.scan([("mod/m.py", "result", "mod/m.py", "R")], root=root)
    assert failures and "cannot verify" in failures[0]
