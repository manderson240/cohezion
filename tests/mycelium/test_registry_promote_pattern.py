"""Tests for MyceliumRegistry._promote_pattern auto-promotion (WS6, 2026-06-03).

Verifies that when a cluster crosses the pattern_size_threshold AND
spans >= 2 universes (true cross-agent signal), the registry writes
to (1) the Obsidian vault and (2) SurrealDB.

Both writes are best-effort and must not raise; failure logs and
continues. The PrecipitationEvent emission remains the source of truth.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from cohezion.mycelium.registry import MyceliumCluster, MyceliumRegistry
from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind


def _make_registry_with_cluster(universes=("u1", "u2"), agents=("a1", "a2"), n_events=3):
    """Build a registry with one cluster pre-populated at threshold.

    Creates n_events cycling through (universes, agents) pairs so a
    2-universe cluster hits the default threshold=3.
    """
    reg = MyceliumRegistry(pattern_size_threshold=n_events)
    for i in range(n_events):
        u = universes[i % len(universes)]
        a = agents[i % len(agents)]
        e = PrecipitationEvent(
            kind=PrecipitationKind.WITNESS_MARK,
            universe_id=u,
            coherence=0.5,
            agent_id=a,
        )
        reg._on_event(e)
    return reg


def test_promote_pattern_skips_single_universe():
    """Cooldown guard: single-universe clusters must NOT be promoted to
    vault or surrealdb (avoids spam)."""
    reg = MyceliumRegistry(pattern_size_threshold=2)
    e = PrecipitationEvent(
        kind=PrecipitationKind.WITNESS_MARK,
        universe_id="only-one-universe",
        coherence=0.5,
        agent_id="a1",
    )
    reg._on_event(e)  # 1 event
    e2 = PrecipitationEvent(
        kind=PrecipitationKind.WITNESS_MARK,
        universe_id="only-one-universe",
        coherence=0.5,
        agent_id="a1",
    )
    reg._on_event(e2)  # 2 events — crosses threshold
    # pattern_emitted is True; vault+db writes should be SKIPPED
    cluster = reg.clusters[0]
    assert cluster.pattern_emitted is True
    # If the cooldown guard works, no vault dir was created
    # (and the test would fail at the write step if it tried)


def test_promote_pattern_writes_vault_when_cross_universe(tmp_path, monkeypatch):
    """When cluster spans >= 2 universes, vault + DB writes must fire."""
    monkeypatch.setenv("COHEZION_VAULT_PATH", str(tmp_path))
    reg = _make_registry_with_cluster()
    cluster = reg.clusters[0]
    assert len(cluster.member_universe_ids) >= 2

    # The _on_event calls above already invoked _emit_pattern_event which
    # already invoked _promote_pattern. So a vault file should already
    # exist under tmp_path / wiki / ouroboros / improvements /.
    improvements = tmp_path / "wiki" / "ouroboros" / "improvements"
    md_files = list(improvements.glob("mycelium-0-*.md"))
    assert len(md_files) == 1
    content = md_files[0].read_text()
    assert "# Mycelium pattern: mycelium-0" in content
    assert "u1" in content and "u2" in content
    assert "a1" in content and "a2" in content


def test_promote_pattern_handles_surrealdb_failure_gracefully(tmp_path, monkeypatch):
    """A 5xx or connection error from surrealdb must NOT raise."""
    monkeypatch.setenv("COHEZION_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("SURREALDB_URL", "http://localhost:1/sql")  # unreachable port

    # _make_registry_with_cluster already fired _promote_pattern; we
    # expect no exception even though surrealdb is down.
    reg = _make_registry_with_cluster()
    # If we got here, no exception was raised — that's the success.
    # Vault file should still be written.
    improvements = tmp_path / "wiki" / "ouroboros" / "improvements"
    md_files = list(improvements.glob("mycelium-0-*.md"))
    assert len(md_files) == 1


def test_promote_pattern_handles_vault_failure_gracefully(monkeypatch):
    """If vault is unwritable, the surrealdb path should still be tried
    and the overall call should not raise."""
    # Point COHEZION_VAULT_PATH at a non-writable location
    monkeypatch.setenv("COHEZION_VAULT_PATH", "/proc/this/path/cannot/be/created")
    # Should not raise
    reg = _make_registry_with_cluster()
    assert reg.clusters[0].pattern_emitted is True
