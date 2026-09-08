import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from cohezion.core.compound_graph_engine import CompoundGraphEngine, LearningRecall

def test_read_before_reasoning_hit():
    engine = CompoundGraphEngine(vault_path=Path("/tmp/vault"))
    mock_rows = [
        {
            "id": "kg_learning:autoharness_verifier",
            "title": "AutoHarness AST bytecode verifier",
            "compound_tool": "cohezion.agi.autoharness_policy",
            "z_vector": [0.5] * 12,
        }
    ]
    with patch.object(engine, "execute_sql", return_value=mock_rows):
        recalls = engine.read_before_reasoning("AutoHarness")
        assert len(recalls) == 1
        assert recalls[0].compound_tool == "cohezion.agi.autoharness_policy"
        assert recalls[0].title == "AutoHarness AST bytecode verifier"

def test_link_compound_loop(tmp_path):
    engine = CompoundGraphEngine(vault_path=tmp_path)
    with patch.object(engine, "execute_sql", return_value=[]) as mock_sql:
        res = engine.link_compound_loop(
            goal_id="arc_dsl_invariance",
            goal_title="ARC DSL Invariance Verification",
            strategy_id="d4_group_test",
            strategy_desc="Apply 16-view D4 dihedral group transformations",
            artifact_path="src/cohezion/arc/d4_transform.py",
            learning_title="D4 Group Homomorphism is Invariant under Reflection",
            compound_tool="cohezion.arc.d4_transform",
        )
        assert res["goal"] == "kg_goal:arc_dsl_invariance"
        assert res["strategy"] == "kg_strategy:d4_group_test"
        assert mock_sql.called

        # Verify Obsidian MOC was written
        moc_file = tmp_path / "00-MOCs" / "compound_arc_dsl_invariance.md"
        assert moc_file.exists()
        content = moc_file.read_text(encoding="utf-8")
        assert "kg_goal:arc_dsl_invariance" in content
        assert "D4 Group Homomorphism" in content
