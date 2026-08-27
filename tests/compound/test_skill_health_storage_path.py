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

from pathlib import Path

from cohezion.compound.skill_health_tracker import SkillHealthTracker


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
