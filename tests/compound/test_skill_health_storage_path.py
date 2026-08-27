"""SkillHealthTracker must persist to a process-independent location.

The default was ``Path("data/skill_health.json")`` -- cwd-relative. A daemon
writing health from directory A and a ``CapabilityMatrix`` constructed in
directory B therefore read and wrote *different files*, and any process without
that path in its cwd loaded zero records silently (``_load`` guards on
``exists()``). That is why the matrix's skill axis measured 0 against a
275-skill library in every runtime.

Anchoring the default removes the cwd fragility. It does NOT by itself populate
the axis -- records still only accumulate once ``update_health()`` persists
during real execution -- so these tests assert the path contract only, and
deliberately do not claim the axis is fixed.
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from cohezion.compound.skill_health_tracker import SkillHealthTracker


def test_suite_is_actually_isolated_from_the_real_state_root() -> None:
    """DISCRIMINATING: red if the conftest isolation fixture stops working.

    Every other test in this file verifies that the tracker HONOURS
    COHEZION_STATE_DIR. None of them verified that anything SETS it -- so with
    the conftest fixture deleted or broken, all 8 stayed green while the suite
    quietly resumed writing into the developer's real ~/.cohezion. Verified
    2026-08-27 by neutralising the fixture: 8/8 still passed.

    Testing the mechanism is not testing the protection. This is the assertion
    that fails when the protection is gone.
    """
    assert os.environ.get("COHEZION_STATE_DIR"), (
        "the session-scoped isolation fixture in tests/conftest.py is not active; "
        "the suite would write skill-health records into the real state root"
    )
    resolved = SkillHealthTracker.default_storage_path()
    assert resolved.parent != Path.home() / ".cohezion", (
        f"tests resolve state to {resolved}, which is the REAL state root"
    )


def test_default_storage_path_is_absolute() -> None:
    """DISCRIMINATING: red for any cwd-relative default."""
    path = SkillHealthTracker()._storage_path
    assert path.is_absolute(), (
        f"default storage path {path} is cwd-relative; processes started from "
        "different directories would read and write different files"
    )


def test_default_storage_path_is_stable_across_cwd(tmp_path: Path, monkeypatch) -> None:
    """The whole point: two processes in different directories must agree."""
    monkeypatch.chdir(tmp_path)
    from_tmp = SkillHealthTracker()._storage_path.resolve()
    monkeypatch.chdir(Path(__file__).parent)
    from_tests = SkillHealthTracker()._storage_path.resolve()
    # .resolve() is load-bearing: a relative Path("data/...") compares EQUAL to
    # itself across directories while resolving to two different files, so an
    # unresolved comparison passes against the very bug this guards.
    assert from_tmp == from_tests


def test_default_filename_is_stable() -> None:
    """The filename is part of the contract regardless of which root is active."""
    assert SkillHealthTracker.default_storage_path().name == "skill_health.json"


def test_explicit_storage_path_is_still_honoured(tmp_path: Path) -> None:
    """Injection must keep working -- tests and callers rely on it."""
    explicit = tmp_path / "custom.json"
    assert SkillHealthTracker(storage_path=explicit)._storage_path == explicit


def test_state_dir_is_overridable_by_environment(tmp_path: Path, monkeypatch) -> None:
    """DISCRIMINATING: red while the default ignores COHEZION_STATE_DIR.

    Regression found 2026-08-27. Anchoring the default to ~/.cohezion fixed the
    cwd problem and created a new one: the test suite began writing records
    named "test" and "FULL_CYCLE_TEST" into the user's REAL state root, where
    that pollution had previously been contained in a repo-local data/ file.
    Anchoring a path is a WIDENING operation -- the original tests checked the
    property that changed (absolute, cwd-stable) and not the property it changed
    into (who else it affects).
    """
    monkeypatch.setenv("COHEZION_STATE_DIR", str(tmp_path / "state"))
    path = SkillHealthTracker.default_storage_path()
    assert path.parent == tmp_path / "state"
    assert path.is_absolute()


def test_environment_override_is_read_per_call(tmp_path: Path, monkeypatch) -> None:
    """The override must not freeze at import, or conftest cannot set it."""
    monkeypatch.setenv("COHEZION_STATE_DIR", str(tmp_path / "first"))
    assert SkillHealthTracker.default_storage_path().parent == tmp_path / "first"
    monkeypatch.setenv("COHEZION_STATE_DIR", str(tmp_path / "second"))
    assert SkillHealthTracker.default_storage_path().parent == tmp_path / "second"


def test_default_without_override_is_still_the_cohezion_state_dir(monkeypatch) -> None:
    """The override is opt-in; production behaviour is unchanged."""
    monkeypatch.delenv("COHEZION_STATE_DIR", raising=False)
    assert SkillHealthTracker.default_storage_path().parent == Path.home() / ".cohezion"


def test_missing_file_yields_no_records_without_raising(tmp_path: Path) -> None:
    """Fail-soft load is preserved (absent file is a valid cold start)."""
    tracker = SkillHealthTracker(storage_path=tmp_path / "absent.json")
    assert tracker._records == {}


# --- concurrency safety (blocking finding, adversarial review 2026-08-27) ------
# Anchoring this file to ~/.cohezion turned a PER-CHECKOUT file into a SHARED one.
# Before the move each of the 11 sibling checkouts and 16 worktrees had its own
# copy, so the collision surface was zero; the move created it. _save() was a bare
# write_text() and _load() an unguarded json.loads() in __init__, so concurrent
# writers corrupt the file -- measured 273 exceptions across 6 processes x 60
# writes, ending in JSONDecodeError. And it is TERMINAL, not transient:
# executor.py constructs SkillHealthTracker() unconditionally, so a corrupt file
# raises on EVERY CompoundExecutor() on the machine until someone deletes it.


def test_corrupt_state_file_does_not_raise(tmp_path: Path) -> None:
    """DISCRIMINATING: red while _load() parses without a guard.

    A shared state file WILL eventually be torn. Failing to start is a far worse
    outcome than starting with no history.
    """
    corrupt = tmp_path / "skill_health.json"
    corrupt.write_text('{"A": {"skill_name": "A"}}{"B": garbage', encoding="utf-8")

    tracker = SkillHealthTracker(storage_path=corrupt)
    assert tracker._records == {}, "a torn file must degrade to an empty history"


def test_truncated_state_file_does_not_raise(tmp_path: Path) -> None:
    """The realistic tear: a write interrupted mid-object."""
    truncated = tmp_path / "skill_health.json"
    truncated.write_text('{"A": {"skill_name": "A", "total_inv', encoding="utf-8")
    assert SkillHealthTracker(storage_path=truncated)._records == {}


def test_save_is_atomic(tmp_path: Path, monkeypatch) -> None:
    """DISCRIMINATING: red while _save() writes in place.

    An interrupted in-place write leaves a truncated file; an interrupted
    tmp+rename leaves the previous good file untouched.
    """
    path = tmp_path / "skill_health.json"
    tracker = SkillHealthTracker(storage_path=path)
    tracker.record_usage("KEEPER", success=True)
    good = path.read_text(encoding="utf-8")

    def boom(*_a, **_kw):
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(KeyboardInterrupt):
        tracker.record_usage("SECOND", success=True)

    assert path.read_text(encoding="utf-8") == good, (
        "an interrupted save must leave the previous state intact"
    )
    assert json.loads(path.read_text(encoding="utf-8"))


def test_concurrent_writers_leave_a_parseable_file(tmp_path: Path) -> None:
    """End-to-end: many writers, file still loads afterwards."""
    path = tmp_path / "skill_health.json"

    def hammer(worker: int) -> None:
        tracker = SkillHealthTracker(storage_path=path)
        for i in range(20):
            tracker.record_usage(f"W{worker}_{i}", success=True)

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(hammer, range(6)))

    json.loads(path.read_text(encoding="utf-8"))  # must not raise
    assert SkillHealthTracker(storage_path=path)._records
