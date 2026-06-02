"""Tests for the read half of the compound learning loop: UnifiedAgent injecting trust-ranked guidance.

The flywheel: ``adapt_skill`` writes accepted fault-guards into a GroundTruthHierarchy; the worker
reads them back into its planning prompt so a fault attributed once improves future tasks. The
DISCRIMINATING tests here assert the injection is *good*, not merely that it *fires*: one-off faults
(trust 0.5) stay OUT, and the block is bounded regardless of how many guards accumulate.

No network: the executor is mocked and we inspect the prompt it was handed.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cohezion.agent.skill_adaptor import AcceptanceCheck, adapt_skill
from cohezion.agent.unified_harness import ExecutionTrace, ToolCall, UnifiedAgent
from cohezion.memory.trust_hierarchy import GroundTruthHierarchy, TrustTier


_HDR_AUTH = "Authoritative memory"  # high-tier directive: treat as ground truth
_HDR_ADVISORY = "Prior observations"  # low-tier directive: verify before relying


def _agent(guidance=None, **kw) -> UnifiedAgent:
    a = UnifiedAgent(executor=AsyncMock(), guidance=guidance, **kw)
    a.executor.execute_task = AsyncMock(return_value=SimpleNamespace(output='{"complete": true}'))
    return a


async def _captured_prompt(agent: UnifiedAgent) -> str:
    trace = ExecutionTrace(task_id="t", start_time="now")
    await agent._plan_next_action(task="scrape a web page", trace=trace, workdir="/tmp", step=0)
    return agent.executor.execute_task.call_args.kwargs["task"]


def _recurring_guard(text: str) -> GroundTruthHierarchy:
    """A hierarchy with one guard that has RECURRED (added twice -> trust 0.667 >= 0.6 floor)."""
    h = GroundTruthHierarchy()
    h.add(text)
    h.add(text)  # re-adoption corroborates -> clears the recurrence-gated floor
    return h


# -- additive: no guidance => prompt unchanged --------------------------------


@pytest.mark.asyncio
async def test_no_guidance_prompt_has_no_memory_block():
    prompt = await _captured_prompt(_agent(guidance=None))
    assert _HDR_AUTH not in prompt and _HDR_ADVISORY not in prompt


# -- the wire fires for a recurring guard, but as ADVISORY (not ground truth) --


@pytest.mark.asyncio
async def test_recurring_guard_is_injected_as_advisory():
    h = _recurring_guard("skill 'bash' guarded against: disk full")  # UNVERIFIED tier
    prompt = await _captured_prompt(_agent(guidance=h))
    assert "disk full" in prompt
    # a model-asserted guard must be advisory — NOT presented as inviolable ground truth
    assert _HDR_ADVISORY in prompt and _HDR_AUTH not in prompt


@pytest.mark.asyncio
async def test_ground_truth_tier_gets_authoritative_directive():
    h = GroundTruthHierarchy()
    h.add("the API base url is http://localhost:13305", TrustTier.GROUND_TRUTH)
    prompt = await _captured_prompt(_agent(guidance=h, guidance_min_trust=0.0))
    assert _HDR_AUTH in prompt  # genuinely high-authority material keeps the ground-truth directive


# -- DISCRIMINATING: a one-off fault (trust 0.5) does NOT flood an unrelated task --------------


@pytest.mark.asyncio
async def test_single_occurrence_guard_excluded():
    h = GroundTruthHierarchy()
    h.add("skill 'bash' guarded against: disk full")  # single add -> trust 0.5 < 0.6 floor
    prompt = await _captured_prompt(_agent(guidance=h))
    assert "disk full" not in prompt  # one-off faults stay out of unrelated tasks
    assert _HDR_AUTH not in prompt and _HDR_ADVISORY not in prompt  # nothing cleared the floor


# -- DISCRIMINATING: injection is bounded regardless of how many guards accumulate -------------


@pytest.mark.asyncio
async def test_injection_is_bounded_by_max_facts():
    h = GroundTruthHierarchy()
    for i in range(12):
        h.add(f"skill 'tool{i}' guarded against: failure mode {i}")
        h.add(f"skill 'tool{i}' guarded against: failure mode {i}")  # recur -> clears floor
    prompt = await _captured_prompt(_agent(guidance=h, guidance_max_facts=5))
    injected_bullets = [ln for ln in prompt.splitlines() if ln.startswith("- [")]
    assert len(injected_bullets) == 5  # capped, not 12 — bounded token cost on the fleet


# -- closed loop: adapt_skill WRITES, the worker READS (same hierarchy) ------------------------


@pytest.mark.asyncio
async def test_closed_loop_adapt_then_inject_same_hierarchy():
    h = GroundTruthHierarchy()
    # a fault recurs across two attempts -> adapt_skill records (and corroborates) the guard
    fault = ExecutionTrace(task_id="t", start_time="now")
    fault.tool_calls.append(ToolCall(tool_name="write", arguments={}, error="disk full"))
    fault.walk = lambda: iter([fault])  # minimal walkable trace
    adapt_skill(fault, acceptance=AcceptanceCheck(), trust=h)
    adapt_skill(fault, acceptance=AcceptanceCheck(), trust=h)  # second occurrence -> clears floor

    agent = _agent(guidance=h)  # SAME hierarchy the orchestrator wrote into
    prompt = await _captured_prompt(agent)
    assert "disk full" in prompt and _HDR_ADVISORY in prompt  # write -> read, end to end (advisory)


# -- per-guard length cap: a huge fault string cannot blow up the prompt -----------------------


@pytest.mark.asyncio
async def test_long_guard_is_length_capped():
    h = GroundTruthHierarchy()
    huge = "x" * 5000
    h.add(f"skill 'bash' guarded against: {huge}")
    h.add(f"skill 'bash' guarded against: {huge}")  # recur -> clears floor
    agent = _agent(guidance=h)
    prompt = await _captured_prompt(agent)
    bullet = next(ln for ln in prompt.splitlines() if ln.startswith("- ["))
    assert len(bullet) < 400  # capped well below 5000 (guidance_max_chars=200 + small overhead)


# -- fail-fast on misconfigured guidance bounds ------------------------------------------------


def test_negative_max_facts_raises():
    with pytest.raises(ValueError, match="guidance_max_facts"):
        UnifiedAgent(executor=AsyncMock(), guidance=GroundTruthHierarchy(), guidance_max_facts=-1)


def test_out_of_range_min_trust_raises():
    with pytest.raises(ValueError, match="guidance_min_trust"):
        UnifiedAgent(executor=AsyncMock(), guidance=GroundTruthHierarchy(), guidance_min_trust=1.5)
