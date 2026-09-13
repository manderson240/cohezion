import json
import pytest
from pathlib import Path
from cohezion.data_mesh.durable_precipitation_bridge import (
    DurablePrecipitationBridge,
    DurableWitnessMark,
)


def test_wikilink_extraction():
    bridge = DurablePrecipitationBridge()
    content = (
        "This relates to [[phase_1_dissolution]] and also [[phase_2_alignment|Phase 2 Functor]]."
    )
    links = bridge._extract_wikilinks(content)
    assert "phase_1_dissolution" in links
    assert "phase_2_alignment" in links


def test_durable_precipitation_lifecycle(tmp_path: Path):
    vault_dir = tmp_path / "vault_mocs"
    bridge = DurablePrecipitationBridge(vault_dir=vault_dir)

    mark = DurableWitnessMark(
        mark_id="test_invariant_node",
        title="Test Invariant Node",
        category="test",
        content="Testing dual persistence with link to [[other_node]].",
        hiho_coherence=0.500,
        metadata={"provenance": "unit_test"},
    )

    res = bridge.persist(mark)

    assert res["status"] == "PRECIPITATED"
    assert res["mark_id"] == "test_invariant_node"

    # Verify Vault Note
    note_path = Path(res["vault_path"])
    assert note_path.exists()
    note_content = note_path.read_text(encoding="utf-8")
    assert "Test Invariant Node" in note_content
    assert "hiho_coherence: 0.5" in note_content

    # Verify Materialized Snapshot
    snapshot_path = vault_dir / "cohezion_state.json"
    assert snapshot_path.exists()
    snapshot_data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert any(entry["mark_id"] == "test_invariant_node" for entry in snapshot_data)


def test_surreal_fail_open(tmp_path: Path):
    vault_dir = tmp_path / "vault_mocs"
    # Point to unreachable port to test fail-open guarantee
    bridge = DurablePrecipitationBridge(
        vault_dir=vault_dir,
        surreal_url="http://127.0.0.1:9999/sql",
    )

    mark = DurableWitnessMark(
        mark_id="fail_open_test",
        title="Fail Open Test",
        content="Should not raise error even if SurrealDB is down.",
    )

    # Must NOT raise exception
    res = bridge.persist(mark)
    assert res["status"] == "PRECIPITATED"
    assert res["surreal_synced"] is False
