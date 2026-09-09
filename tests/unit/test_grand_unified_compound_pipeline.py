import pytest

from cohezion.compound.grand_unified_compound_pipeline import GrandUnifiedCompoundPipeline


@pytest.mark.asyncio
async def test_grand_unified_compound_pipeline_execution():
    pipeline = GrandUnifiedCompoundPipeline()
    res = await pipeline.execute_mission(
        "AutonomousBreadthAndDepthExpansion", target_metric="coherence"
    )

    assert res.mission_id.startswith("mission_")
    assert res.classified_tier == "npu"
    assert res.poincare_conformal_factor >= 2.0
    assert res.baml_validated is True
    assert res.autoharness_verified is True
    assert res.zkfv_verified is True
    assert res.sheaf_consistent is True
    assert res.sheaf_dirichlet_energy < 0.05
    assert res.kanban_persisted is True
    assert res.telemetry_emitted is True
    assert res.execution_latency_ms < 500.0  # Entire 10-subsystem cycle completes in sub-500ms
