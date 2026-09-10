"""Unit tests for VaultNeuronGraph and ExperientialPrior (SurrealDB 3.x)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.learning.vault_neuron_reader import (
    ExperientialPrior,
    VaultNeuronGraph,
    VaultNeuronWriter,
)


def test_experiential_prior_dataclass():
    prior = ExperientialPrior(
        neuron_id="neuron_123",
        category="autopoiesis",
        similarity=0.98,
        success_rate=1.0,
        action_ir="AST_CANARY",
        quality_score=0.92,
        delta_entropy=-0.04,
    )
    assert prior.neuron_id == "neuron_123"
    assert prior.similarity == 0.98
    assert prior.delta_entropy == -0.04


@pytest.mark.asyncio
async def test_vault_neuron_graph_record_and_synapse():
    mock_client = MagicMock()
    mock_client.query = AsyncMock(return_value=[{"result": []}])

    graph = VaultNeuronGraph(surreal_client=mock_client)
    neuron_id = await graph.record_neuron(
        task_id="task_test_1",
        category="code_synthesis",
        success=True,
        tokens=128,
        node="strix_halo_npu",
        model="deepseek-r1-0528-8b-FLM",
        quality_score=0.95,
        delta_entropy=-0.015,
        embedding=[0.05] * 256,
        previous_neuron_id="neuron_prev_0",
    )

    assert "neuron_task_test_1" in neuron_id
    # Schema query + upsert + relate
    assert mock_client.query.call_count >= 3


@pytest.mark.asyncio
async def test_vault_neuron_graph_retrieve_priors():
    mock_client = MagicMock()
    mock_client.query = AsyncMock(
        return_value=[
            {
                "result": [
                    {
                        "id": "experiential_neuron:test_1",
                        "category": "physics_sim",
                        "sim": 0.945,
                        "quality_score": 0.88,
                        "delta_entropy": -0.02,
                    }
                ]
            }
        ]
    )

    graph = VaultNeuronGraph(surreal_client=mock_client)
    priors = await graph.retrieve_experiential_priors([0.02] * 256, k=3)

    assert len(priors) == 1
    assert priors[0].similarity == 0.945
    assert priors[0].delta_entropy == -0.02
    assert priors[0].quality_score == 0.88


def test_vault_neuron_writer_has_graph_property():
    writer = VaultNeuronWriter.get_instance()
    assert isinstance(writer.graph, VaultNeuronGraph)
