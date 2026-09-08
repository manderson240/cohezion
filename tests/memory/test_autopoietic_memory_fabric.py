import json
import pytest
from pathlib import Path
from cohezion.memory.autopoietic_memory_fabric import (
    AutopoieticMemoryFabric,
    AutopoieticHealthReport,
    POINCARE_DIM,
    COHESION_THRESHOLD,
)
from cohezion.agi.autoharness_policy import AutoHarnessPolicy


def test_poincare_2048d_embedding():
    fabric = AutopoieticMemoryFabric()
    pt = fabric._embed_node_to_poincare("test_node", "Test Node Title")
    assert pt.dim == POINCARE_DIM
    norm_sq = sum(c * c for c in pt.coords)
    assert norm_sq < 1.0, f"Poincaré point norm^2 {norm_sq} must be < 1.0"


def test_fabric_inspection_and_autopoietic_healing(tmp_path: Path):
    vault_dir = tmp_path / "mock_vault"
    vault_dir.mkdir(parents=True, exist_ok=True)

    # Populate mock snapshot with 3 nodes: 2 connected, 1 orphan
    snapshot_path = vault_dir / "cohezion_state.json"
    snapshot_records = [
        {"mark_id": "node_a", "title": "Node A", "wikilinks": ["node_b"], "hiho_coherence": 0.50},
        {"mark_id": "node_b", "title": "Node B", "wikilinks": [], "hiho_coherence": 0.50},
        {"mark_id": "orphan_c", "title": "Orphan C", "wikilinks": [], "hiho_coherence": 0.50},
    ]
    snapshot_path.write_text(json.dumps(snapshot_records), encoding="utf-8")

    # Create dummy master MOC
    master_moc = vault_dir / "000_Master_Transcendence_MOC.md"
    master_moc.write_text("# Master MOC\n", encoding="utf-8")

    fabric = AutopoieticMemoryFabric(vault_dir=vault_dir)

    # 1. Inspect
    report = fabric.inspect_fabric()
    assert report.total_nodes == 3
    assert "orphan_c" in report.unanchored_nodes
    assert report.cohesion_index < 1.0

    # 2. Heal
    healed_report = fabric.auto_heal_fabric()
    assert healed_report.cohesion_index == 1.0
    assert healed_report.healed_edges_count > 0
    assert len(healed_report.unanchored_nodes) == 0
    assert healed_report.autoharness_verified is True

    # 3. Verify Master MOC got updated with healed link
    moc_content = master_moc.read_text(encoding="utf-8")
    assert "orphan_c" in moc_content or "Orphan C" in moc_content


def test_reconcile_and_persist_lifecycle(tmp_path: Path):
    vault_dir = tmp_path / "mock_vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    master_moc = vault_dir / "000_Master_Transcendence_MOC.md"
    master_moc.write_text("# Master MOC\n", encoding="utf-8")

    fabric = AutopoieticMemoryFabric(vault_dir=vault_dir)
    res = fabric.reconcile_and_persist()

    assert res["status"] == "PRECIPITATED"
    assert res["mark_id"] == "phase_4_autopoietic_memory_fabric"

    note_path = Path(res["vault_path"])
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "Phase 4: Transcendent Cohesion" in content
    assert "2048D" in content
