"""Unit tests for the AutoHarness implementation (arXiv:2603.03329v1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.inference.autoharness import (
    AutoHarnessEngine,
    CodeAsActionVerifier,
    HarnessAsPolicy,
    ThompsonSamplingSearch,
)


def test_thompson_sampling_search():
    """Verify that ThompsonSamplingSearch can add and select hypotheses."""
    search = ThompsonSamplingSearch()

    code_a = "def is_legal_action(a): return True, ''"
    code_b = "def is_legal_action(a): return False, 'always invalid'"

    id_a = search.add_hypothesis(code_a, "Harness A")
    id_b = search.add_hypothesis(code_b, "Harness B")

    assert id_a != id_b
    assert search.root_id == id_a

    # Run updates to test selection preference
    hyp_a = search.hypotheses[id_a]
    hyp_b = search.hypotheses[id_b]

    # Harness A succeeds 10 times
    for _ in range(10):
        hyp_a.update(success=True)
    # Harness B fails 10 times
    for _ in range(10):
        hyp_b.update(success=False)

    # Over multiple selections, A should dominate B
    selections = [search.select_best().code_id for _ in range(100)]
    assert selections.count(id_a) > selections.count(id_b)


@pytest.mark.asyncio
async def test_code_as_action_verifier():
    """Verify that CodeAsActionVerifier can compile, run, and mutate code harnesses."""
    verifier = CodeAsActionVerifier("test_arena")

    rules = "Action must start with 'move_'"

    # Initialize with baseline stub
    stub = (
        "def is_legal_action(action: str) -> tuple[bool, str]:\n"
        "    if action.startswith('move_'):\n"
        "        return True, ''\n"
        "    return False, 'Action must start with move_'\n"
    )

    code_id = await verifier.initialize(rules, baseline_code_stub=stub)
    assert verifier.active_code_id == code_id

    # Test verification
    ok, err = verifier.verify("move_left")
    assert ok is True
    assert err == ""

    ok, err = verifier.verify("jump")
    assert ok is False
    assert "move_" in err

    # Record feedback & mutate
    mutated_code = (
        "def is_legal_action(action: str) -> tuple[bool, str]:\n"
        "    if action.startswith('move_') or action == 'teleport':\n"
        "        return True, ''\n"
        "    return False, 'Invalid action'\n"
    )

    with patch.object(
        verifier, "_call_local_llm", new_callable=AsyncMock, return_value=mutated_code
    ):
        new_id = await verifier.record_feedback("teleport", "Invalid action 'teleport'")
        assert new_id != code_id
        assert verifier.active_code_id == new_id

        # Test verification with mutated code
        ok, err = verifier.verify("teleport")
        assert ok is True

        ok, err = verifier.verify("jump")
        assert ok is False


@pytest.mark.asyncio
async def test_harness_as_policy():
    """Verify that HarnessAsPolicy compiles traces into a deterministic function."""
    policy = HarnessAsPolicy("grid_world")

    # Add traces mapping context coordinates to correct move
    policy.add_trace({"x": 1, "y": 2, "target_x": 2, "target_y": 2}, "move_right")
    policy.add_trace({"x": 2, "y": 2, "target_x": 2, "target_y": 3}, "move_up")

    compiled_code = (
        "def decide_action(context: dict) -> str:\n"
        "    if context['x'] < context['target_x']:\n"
        "        return 'move_right'\n"
        "    if context['y'] < context['target_y']:\n"
        "        return 'move_up'\n"
        "    return 'idle'\n"
    )

    with patch.object(
        policy, "_call_local_llm", new_callable=AsyncMock, return_value=compiled_code
    ):
        compiled_success = await policy.compile_policy()
        assert compiled_success is True
        assert policy.compiled_code == compiled_code

        # Test execution of compiled policy
        action = policy.execute({"x": 1, "y": 2, "target_x": 2, "target_y": 2})
        assert action == "move_right"

        action = policy.execute({"x": 2, "y": 2, "target_x": 2, "target_y": 3})
        assert action == "move_up"


@pytest.mark.asyncio
async def test_autoharness_engine():
    """Verify the overall AutoHarnessEngine execution loop."""
    engine = AutoHarnessEngine("maze")

    rules = "Actions must be 'north', 'south', 'east', 'west'"
    stub = (
        "def is_legal_action(action: str) -> tuple[bool, str]:\n"
        "    if action in ['north', 'south', 'east', 'west']:\n"
        "        return True, ''\n"
        "    return False, 'Invalid direction'\n"
    )

    with patch.object(
        engine.verifier, "_call_local_llm", new_callable=AsyncMock, return_value=stub
    ):
        await engine.initialize(rules)

        def agent_fn(ctx):
            # First execution returns 'fly', which is illegal
            if ctx.get("trial") == 0:
                ctx["trial"] = 1
                return "fly"
            return "north"

        context = {"trial": 0}

        # The engine should reject 'fly', retry, get 'north', verify it as valid, and record trace
        action = await engine.execute_step(context, agent_fn)
        assert action == "north"
        assert len(engine.policy.traces) == 1
        assert engine.policy.traces[0][1] == "north"
