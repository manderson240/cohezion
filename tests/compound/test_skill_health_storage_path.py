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


def test_default_lives_in_the_cohezion_state_dir() -> None:
    """Matches the other ~/.cohezion/* state files rather than inventing a home."""
    path = SkillHealthTracker()._storage_path
    assert path.parent == Path.home() / ".cohezion"
    assert path.name == "skill_health.json"


def test_explicit_storage_path_is_still_honoured(tmp_path: Path) -> None:
    """Injection must keep working -- tests and callers rely on it."""
    explicit = tmp_path / "custom.json"
    assert SkillHealthTracker(storage_path=explicit)._storage_path == explicit


def test_missing_file_yields_no_records_without_raising(tmp_path: Path) -> None:
    """Fail-soft load is preserved (absent file is a valid cold start)."""
    tracker = SkillHealthTracker(storage_path=tmp_path / "absent.json")
    assert tracker._records == {}
