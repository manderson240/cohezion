"""Tests for ContextManager caching (Task #14).

Verifies that ``_find_project_root`` and skill-context YAML reads are
cached at the class level — second calls for the same key short-circuit
filesystem access.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cohezion.compound.context_integration import ContextManager


@pytest.fixture(autouse=True)
def _reset_caches():
    """Ensure class-level caches do not leak between tests."""
    ContextManager.clear_caches()
    yield
    ContextManager.clear_caches()


@pytest.fixture()
def context_root(tmp_path: Path) -> Path:
    """Create a minimal project root containing .context/."""
    ctx = tmp_path / ".context"
    ctx.mkdir()
    (ctx / "traceability").mkdir()
    (ctx / "skills").mkdir()
    return tmp_path


def test_project_root_cached_on_second_call(context_root: Path):
    """[P0] Filesystem traversal must only happen once per cwd."""
    real_exists = Path.exists
    call_counter: dict[str, int] = {"count": 0}

    def counting_exists(self: Path) -> bool:
        # Only count probes for the .context directory — that is the
        # signal _find_project_root uses to identify the project root.
        if self.name == ".context":
            call_counter["count"] += 1
        return real_exists(self)

    with patch.object(Path, "cwd", return_value=context_root):
        with patch.object(Path, "exists", counting_exists):
            mgr1 = ContextManager()
            first_count = call_counter["count"]
            mgr2 = ContextManager()
            second_count = call_counter["count"]

    assert first_count >= 1, "first call should probe .context at least once"
    assert second_count == first_count, (
        "second call must hit cache and skip filesystem probes "
        f"(probes went {first_count} -> {second_count})"
    )
    assert mgr1.project_root == context_root
    assert mgr2.project_root == context_root


def test_cache_returns_same_path(context_root: Path):
    """[P0] Two calls from the same cwd return identical Path objects."""
    with patch.object(Path, "cwd", return_value=context_root):
        mgr1 = ContextManager()
        mgr2 = ContextManager()

    assert mgr1.project_root == mgr2.project_root
    # Cache should store one entry keyed on str(cwd) with shape
    # (timestamp, value).
    assert str(context_root) in ContextManager._root_cache
    ts, value = ContextManager._root_cache[str(context_root)]
    assert value == context_root
    assert isinstance(ts, float)


def test_cache_per_working_directory(tmp_path: Path):
    """[P0] Different CWDs produce distinct cache entries."""
    root_a = tmp_path / "proj_a"
    root_b = tmp_path / "proj_b"
    for r in (root_a, root_b):
        (r / ".context").mkdir(parents=True)

    with patch.object(Path, "cwd", return_value=root_a):
        mgr_a = ContextManager()
    with patch.object(Path, "cwd", return_value=root_b):
        mgr_b = ContextManager()

    assert mgr_a.project_root == root_a
    assert mgr_b.project_root == root_b
    cache = ContextManager._root_cache
    assert str(root_a) in cache
    assert str(root_b) in cache
    # Compare the cached Path values (entries are (timestamp, Path)).
    assert cache[str(root_a)][1] != cache[str(root_b)][1]


def test_root_cache_ttl_expiry(context_root: Path, monkeypatch):
    """[P0] Cache entries past CACHE_TTL_SECONDS are evicted on read.

    Strategy: monkeypatch ``time.monotonic`` so we can advance the clock
    deterministically, then assert that a probe AFTER the TTL boundary
    triggers a fresh filesystem traversal (cached entry was evicted).
    """
    import time as _time

    # Virtual clock controlled by the test.
    fake_now = {"t": 1000.0}

    def fake_monotonic():
        return fake_now["t"]

    monkeypatch.setattr(_time, "monotonic", fake_monotonic)

    real_exists = Path.exists
    probe_count = {"n": 0}

    def counting_exists(self: Path) -> bool:
        if self.name == ".context":
            probe_count["n"] += 1
        return real_exists(self)

    with patch.object(Path, "cwd", return_value=context_root):
        with patch.object(Path, "exists", counting_exists):
            ContextManager()  # warm cache at t=1000
            n_after_warm = probe_count["n"]

            # Advance clock just past TTL.
            fake_now["t"] = 1000.0 + ContextManager.CACHE_TTL_SECONDS + 0.1
            ContextManager()  # should miss → traverse again
            n_after_expiry = probe_count["n"]

    assert n_after_expiry > n_after_warm, (
        f"Expired cache entry should trigger a fresh probe; "
        f"probes went {n_after_warm} -> {n_after_expiry}"
    )


def test_thread_safety_documented():
    """[P2] Doc invariant: caches advertise their non-thread-safe contract.

    The class docstring / module comments must call out that concurrent
    writers may double-traverse (benign) but never observe partial state.
    This test ensures the contract is captured in code so future readers
    don't assume thread safety.
    """
    import inspect

    src = inspect.getsource(ContextManager)
    assert "thread-safe" in src.lower() or "concurrency" in src.lower(), (
        "ContextManager must document its thread-safety contract"
    )


def test_skill_context_yaml_cached(tmp_path: Path):
    """[P1] Skill context YAML is read only once per file path."""
    pytest.importorskip("yaml")

    ctx = tmp_path / ".context"
    (ctx / "traceability").mkdir(parents=True)
    skill_dir = ctx / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    yaml_path = skill_dir / "context.yaml"
    yaml_path.write_text("name: demo\nbudget: 50\n")

    manifest = {
        "version": "1.0.0",
        "core_files": [],
        "skills": {"demo": {"context_file": "skills/demo/context.yaml"}},
    }
    (ctx / "traceability" / "manifest.json").write_text(json.dumps(manifest))

    mgr = ContextManager(tmp_path)

    # First read: hits disk.
    cfg1 = mgr.load_skill_context("demo")
    # Second read: should hit the class-level cache without reopening
    # the file.
    real_open = open
    open_calls: list[str] = []

    def tracking_open(path, *args, **kwargs):
        open_calls.append(str(path))
        return real_open(path, *args, **kwargs)

    with patch("builtins.open", side_effect=tracking_open):
        cfg2 = mgr.load_skill_context("demo")

    # Manifest may be re-read but YAML must NOT be re-opened.
    assert all(str(yaml_path) not in p for p in open_calls), (
        f"YAML should not be re-opened on cached read; open_calls={open_calls}"
    )
    assert cfg1 == cfg2 == {"name": "demo", "budget": 50}
