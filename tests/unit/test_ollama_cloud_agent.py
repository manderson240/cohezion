"""Unit tests for OllamaCloudAgent and OllamaCloudSwarm with AutoHarness and AutoContext."""

import pytest
from unittest.mock import AsyncMock, patch

from cohezion.agents.ollama_cloud_agent import (
    AutoContextState,
    OllamaCloudAgent,
    OllamaCloudModel,
    OllamaCloudSwarm,
)
from cohezion.agi.autoharness_policy import AutoHarnessPolicy


def test_autocontext_2048d_poincare_projection() -> None:
    """Validate that AutoContext continuously projects into the 2048D Poincaré unit ball."""
    state = AutoContextState.from_text("ARC-AGI-2 Top 10 Ascent Goal", state_id="step_0")

    assert state.dimension == 2048
    assert len(state.point.coords) == 2048
    assert state.point.norm < 1.0
    assert state.conformal_factor >= 2.0
    assert len(state.trajectory) == 1

    # Take a geodesic step
    state.step("Synthesized LoRA SFT139 Invariant Verifier", state_id="step_1")
    assert len(state.trajectory) == 2
    assert state.point.norm < 1.0
    assert state.conformal_factor >= 2.0


def test_autoharness_domain_invariants() -> None:
    """Validate AutoHarness policy enforcement on ARC, RSNA, and CASMI domain states."""
    agent = OllamaCloudAgent(
        name="test_agent",
        role="Domain Verifier",
        model=OllamaCloudModel.DEEPSEEK_V4_PRO,
        system_prompt="Test agent prompt",
    )

    # 1. ARC Grid Invariant: Valid
    valid_grid = {"grid": [[1, 2], [3, 4]]}
    res_valid = agent.harness.evaluate_policy("arc_grid_invariants", valid_grid)
    assert res_valid.allowed is True

    # ARC Grid Invariant: Invalid color 12
    invalid_grid = {"grid": [[1, 12], [3, 4]]}
    res_invalid = agent.harness.evaluate_policy("arc_grid_invariants", invalid_grid)
    assert res_invalid.allowed is False

    # 2. RSNA Monotonicity: P(Abnormal) >= max P_k
    valid_rsna = {"p_abnormal": 0.85, "sub_conditions": [0.4, 0.7, 0.2]}
    assert agent.harness.evaluate_policy("rsna_monotonicity", valid_rsna).allowed is True

    invalid_rsna = {"p_abnormal": 0.50, "sub_conditions": [0.4, 0.9, 0.2]}
    assert agent.harness.evaluate_policy("rsna_monotonicity", invalid_rsna).allowed is False

    # 3. CASMI Mass Tolerance: < 5 ppm
    valid_casmi = {"delta_ppm": 2.1}
    assert agent.harness.evaluate_policy("casmi_mass_tolerance", valid_casmi).allowed is True

    invalid_casmi = {"delta_ppm": 8.5}
    assert agent.harness.evaluate_policy("casmi_mass_tolerance", invalid_casmi).allowed is False


@pytest.mark.asyncio
async def test_ollama_cloud_agent_turn_mocked() -> None:
    """Validate agent execution turn, AutoContext injection, and AutoHarness verification."""
    agent = OllamaCloudAgent(
        name="arc2_solver",
        role="ARC-AGI-2 Solver",
        model=OllamaCloudModel.DEEPSEEK_V4_PRO,
        system_prompt="Solve ARC puzzles.",
    )

    mock_resp_json = {
        "message": {
            "content": (
                "Here is the verified invariant solver function:\n"
                "```python\n"
                "def solve_grid(grid: list[list[int]]) -> list[list[int]]:\n"
                "    \"\"\"Rotate and reflect invariant colors.\"\"\"\n"
                "    return [[cell for cell in row] for row in grid]\n"
                "```\n"
            )
        },
        "thinking": "We analyze the D4 dihedral group and verify symmetry.",
    }

    mock_http_response = AsyncMock()
    mock_http_response.status_code = 200
    mock_http_response.json = lambda: mock_resp_json

    with patch("httpx.AsyncClient.post", return_value=mock_http_response):
        result = await agent.execute_turn(goal="Solve dihedral reflection task #42")

        assert result.agent_name == "arc2_solver"
        assert result.autoharness_verified is True
        assert len(result.violations) == 0
        assert result.autocontext_conformal_factor >= 2.0
        assert "def solve_grid" in result.response


@pytest.mark.asyncio
async def test_ollama_cloud_swarm_initialization_and_mission() -> None:
    """Validate OllamaCloudSwarm initializes specialists and runs missions."""
    swarm = OllamaCloudSwarm()

    assert "arc2_solver" in swarm.agents
    assert "arc3_explorer" in swarm.agents
    assert "gemma_paper_lead" in swarm.agents
    assert "rsna_efficiency_lead" in swarm.agents

    mock_resp_json = {
        "message": {"content": "Strategy confirmed. AutoHarness verifier active."},
        "thinking": "Detailed reasoning.",
    }
    mock_http_response = AsyncMock()
    mock_http_response.status_code = 200
    mock_http_response.json = lambda: mock_resp_json

    with patch("httpx.AsyncClient.post", return_value=mock_http_response), \
         patch("cohezion.agents.ollama_cloud_agent.persist_item") as mock_persist:
        results = await swarm.run_mission(
            mission_name="Top 10 Ascent Sprint",
            goals={
                "arc2_solver": "Close +2.08% gap on ARC-AGI-2",
                "rsna_efficiency_lead": "Validate FP16 sub-15 min latency",
            },
        )

        assert len(results) == 2
        assert "arc2_solver" in results
        assert "rsna_efficiency_lead" in results
        assert mock_persist.called
