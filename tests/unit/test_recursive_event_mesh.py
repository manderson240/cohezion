import pytest
from unittest.mock import patch, MagicMock
from cohezion.data_mesh.recursive_event_mesh import (
    DynamicRecursiveDataMesh,
    AdaptiveMeshMarkovChain,
    MeshState,
)
from cohezion.reliability.oom_guard import MemoryState

def test_adaptive_markov_chain():
    mc = AdaptiveMeshMarkovChain()
    initial_probs = mc.get_transition_probs(MeshState.SWEEP)
    assert len(initial_probs) == 5
    assert sum(initial_probs) == pytest.approx(1.0)

    # Reinforce SWEEP -> RESEARCH with high reward
    mc.record_transition(MeshState.SWEEP, MeshState.RESEARCH, reward=2.0)
    updated_probs = mc.get_transition_probs(MeshState.SWEEP)
    research_idx = mc.states.index(MeshState.RESEARCH)
    assert updated_probs[research_idx] > initial_probs[research_idx]

def test_sweep_internal_codebase():
    mesh = DynamicRecursiveDataMesh()
    with patch(
        "cohezion.reliability.oom_guard.OOMGuard.get_memory_state",
        return_value=MemoryState(
            available_gb=25.0,
            total_gb=128.0,
            swap_used_gb=0.0,
            shmem_gb=0.5,
            is_safe=True,
            dynamic_floor_gb=20.0,
        ),
    ):
        res = mesh.sweep_internal_codebase()
        assert res.is_success is True
        assert res.value is not None
        assert res.value.is_safe is True
        assert res.value.available_memory_gb == 25.0

def test_research_bleeding_edge():
    mesh = DynamicRecursiveDataMesh()
    res = mesh.research_bleeding_edge()
    assert res.is_success is True
    assert res.value is not None
    assert len(res.value.top_papers) >= 2
    # Verify AMD skills catalog integration
    assert isinstance(res.value.amd_skills_active, list)

@pytest.mark.asyncio
async def test_execute_mesh_cycle():
    mock_bus = MagicMock()
    mock_bus.publish = MagicMock()
    async def mock_pub(evt):
        return None
    mock_bus.publish.side_effect = mock_pub

    mock_graph = MagicMock()
    mock_graph.link_compound_loop.return_value = {
        "goal": "kg_goal:test",
        "strategy": "kg_strategy:test",
        "artifact": "kg_artifact:test",
        "learning": "kg_learning:test",
    }

    mesh = DynamicRecursiveDataMesh(event_bus=mock_bus, graph_engine=mock_graph)
    with patch(
        "cohezion.reliability.oom_guard.OOMGuard.get_memory_state",
        return_value=MemoryState(
            available_gb=25.0,
            total_gb=128.0,
            swap_used_gb=0.0,
            shmem_gb=0.5,
            is_safe=True,
            dynamic_floor_gb=20.0,
        ),
    ):
        cycle_res = await mesh.execute_cycle("cycle_unit_001")
        assert cycle_res.is_success is True
        assert cycle_res.value is not None
        out = cycle_res.value
        assert out.cycle_id == "cycle_unit_001"
        assert out.alignment_score > 0.0
        assert mock_graph.link_compound_loop.called
        assert mock_bus.publish.called
