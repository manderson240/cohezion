"""RED tests for the smart router (route_by_capability) and the
extend_claude_aligned variant.

Contracts:

route_by_capability(task, required_modes, prompt_estimate_tokens)
  → (ModelEntry, InferenceParams) | None
  - filters registry by task_affinity ⊇ {task}
  - rejects entries with profile=None (RecipeGuard.assert_card_present)
  - rejects candidates whose profile.min_ctx > available_ctx
  - scores by strengths ∩ task; penalizes for known weaknesses that match
  - prefers local over cloud unless a card weakness explicitly matches
  - returns None if no candidate clears the filters

extend_claude_aligned(prompt, *, params, quality_threshold=0.8, max_local_attempts=2, timeout=30.0)
  → RouteResult
  - `params` is keyword-only and required
  - raises TypeError if params is missing
  - the underlying dispatch honors params.model_id (does NOT pick a different model)
  - the quality gate keeps the local result if it clears (length + confidence)
  - escalates to claude_model on gate failure (same behavior as extend_claude)
  - existing extend_claude is unchanged
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.inference.capability_profile import CapabilityProfile
from cohezion.inference.fleet import extend_claude_aligned
from cohezion.inference.model_card_harness import InferenceParams
from cohezion.inference.registry import (
    KVQuant,
    Lane,
    ModelEntry,
    Task,
    WeightQuant,
)
from cohezion.inference.route_by_capability import (
    route_by_capability,
)


def _good_profile(
    model_id: str = "test/model",
    *,
    family: str = "test",
    strengths: tuple[str, ...] = ("code",),
    weaknesses: tuple[str, ...] = (),
    min_ctx: int = 512,
    optimal_ctx: int = 8192,
    modes: tuple[str, ...] = ("chat",),
) -> CapabilityProfile:
    return CapabilityProfile(
        model_id=model_id,
        family=family,
        supported_modes=frozenset(modes),
        optimal_ctx=optimal_ctx,
        min_ctx=min_ctx,
        strengths=frozenset(strengths),
        weaknesses=frozenset(weaknesses),
        sampling_sweet_spot={"temperature": 0.6, "top_p": 0.95},
        prompt_template_fingerprint="chatml",
        thinking_mode="never",
        known_failure_modes=(),
        source_url=f"https://huggingface.co/{model_id}",
        read_at=datetime(2026, 6, 4, tzinfo=UTC),
    )


def _make_entry(
    model_id: str,
    *,
    task: Task = Task.CODE_GEN,
    lane: Lane = Lane.IGPU_UNIFIED,
    profile: CapabilityProfile | None = None,
) -> ModelEntry:
    return ModelEntry(
        model_id=model_id,
        lane=lane,
        endpoint="http://localhost:9999/v1",
        runtime_backend="llamacpp_hip",
        task_affinity=frozenset({task}),
        weight_quant=WeightQuant.Q4_K_M,
        context_window=32768,
        kv_quant=KVQuant(),
        profile=profile,
    )


# ── route_by_capability: filter and score ──────────────────────────────────


def test_route_by_capability_returns_none_when_no_candidate_matches_task():
    """A registry of code-only entries cannot serve a REASONING task."""
    entry = _make_entry("only/code", task=Task.CODE_GEN)
    registry = type("R", (), {"models": {entry.model_id: entry}})()
    with patch("cohezion.inference.route_by_capability.get_registry", return_value=registry):
        result = route_by_capability(
            task=Task.REASONING,
            required_modes=frozenset(),
            prompt_estimate_tokens=1000,
        )
    assert result is None


def test_route_by_capability_rejects_cardless_entry():
    """A ModelEntry with profile=None cannot be dispatched (recipe_guard rule)."""
    cardless = _make_entry("cardless", task=Task.CODE_GEN, profile=None)
    registry = type("R", (), {"models": {cardless.model_id: cardless}})()
    with patch("cohezion.inference.route_by_capability.get_registry", return_value=registry):
        result = route_by_capability(
            task=Task.CODE_GEN,
            required_modes=frozenset(),
            prompt_estimate_tokens=1000,
        )
    assert result is None


def test_route_by_capability_rejects_candidate_below_min_ctx():
    """If prompt_estimate > min_ctx * 1.2, the model can't safely serve the task."""
    small_ctx = _make_entry(
        "tiny",
        profile=_good_profile(
            "tiny",
            min_ctx=512,
            optimal_ctx=1024,
        ),
    )
    registry = type("R", (), {"models": {small_ctx.model_id: small_ctx}})()
    with patch("cohezion.inference.route_by_capability.get_registry", return_value=registry):
        # prompt needs 10000 tokens, tiny has min_ctx 512 → reject
        result = route_by_capability(
            task=Task.CODE_GEN,
            required_modes=frozenset(),
            prompt_estimate_tokens=10000,
        )
    assert result is None


def test_route_by_capability_prefers_local_over_cloud():
    """A local candidate with a card profile beats a cloud one when both
    can serve the task."""
    local = _make_entry(
        "local/code",
        task=Task.CODE_GEN,
        lane=Lane.IGPU_UNIFIED,
        profile=_good_profile("local/code", strengths=("code",)),
    )
    cloud = _make_entry(
        "cloud/code",
        task=Task.CODE_GEN,
        lane=Lane.CLOUD_CLAUDE,
        profile=_good_profile("cloud/code", strengths=("code",)),
    )
    registry = type("R", (), {"models": {local.model_id: local, cloud.model_id: cloud}})()
    with patch("cohezion.inference.route_by_capability.get_registry", return_value=registry):
        entry, _params = route_by_capability(
            task=Task.CODE_GEN,
            required_modes=frozenset(),
            prompt_estimate_tokens=1000,
        )
    assert entry is not None
    assert entry.lane == Lane.IGPU_UNIFIED


def test_route_by_capability_penalizes_weakness_matching_task():
    """A candidate whose card lists 'long_context' as a weakness is de-prioritized
    when the task is LONG_HORIZON, even if it has 'long_context' in strengths."""
    weak_for_long = _make_entry(
        "weak",
        task=Task.LONG_HORIZON,
        lane=Lane.IGPU_UNIFIED,
        profile=_good_profile(
            "weak",
            strengths=("long_context",),
            weaknesses=("long_context",),  # card says it degrades on long ctx
        ),
    )
    healthy = _make_entry(
        "healthy",
        task=Task.LONG_HORIZON,
        lane=Lane.CPU,
        profile=_good_profile(
            "healthy",
            strengths=("long_context",),
        ),
    )
    registry = type(
        "R", (), {"models": {weak_for_long.model_id: weak_for_long, healthy.model_id: healthy}}
    )()
    with patch("cohezion.inference.route_by_capability.get_registry", return_value=registry):
        entry, _params = route_by_capability(
            task=Task.LONG_HORIZON,
            required_modes=frozenset(),
            prompt_estimate_tokens=2048,
        )
    assert entry is not None
    # The "weak" candidate is downgraded; "healthy" wins.
    assert entry.model_id == "healthy"


def test_route_by_capability_filters_by_required_modes():
    """A model that doesn't support `tool_use` can't serve a task that requires it."""
    no_tools = _make_entry(
        "no-tools",
        task=Task.GENERAL,
        profile=_good_profile("no-tools", modes=("chat",)),
    )
    with_tools = _make_entry(
        "with-tools",
        task=Task.GENERAL,
        profile=_good_profile("with-tools", modes=("chat", "tool_use")),
    )
    registry = type(
        "R", (), {"models": {no_tools.model_id: no_tools, with_tools.model_id: with_tools}}
    )()
    with patch("cohezion.inference.route_by_capability.get_registry", return_value=registry):
        entry, _params = route_by_capability(
            task=Task.GENERAL,
            required_modes=frozenset({"tool_use"}),
            prompt_estimate_tokens=100,
        )
    assert entry is not None
    assert entry.model_id == "with-tools"


def test_route_by_capability_returns_inference_params_with_card_aligned_sampling():
    """The returned InferenceParams carries the card's sampling sweet spot,
    not the lane's default."""
    entry = _make_entry(
        "sweet",
        task=Task.CODE_GEN,
        profile=_good_profile(
            "sweet",
            strengths=("code",),
        ),
    )
    registry = type("R", (), {"models": {entry.model_id: entry}})()
    with patch("cohezion.inference.route_by_capability.get_registry", return_value=registry):
        _entry, params = route_by_capability(
            task=Task.CODE_GEN,
            required_modes=frozenset(),
            prompt_estimate_tokens=1000,
        )
    assert params is not None
    assert params.model_id == "sweet"
    # Card-derived sampling is preserved (the exact key/path doesn't
    # matter; the point is the params are non-default).
    assert params.extra_body.get("temperature") == 0.6
    # The point is that the params are non-default (RecipeGuard.assert_aligned passes)
    from cohezion.inference.recipe_guard import RecipeGuard

    RecipeGuard.assert_aligned(params)


# ── extend_claude_aligned: keyword-only params, behavior preserved ──────────


@pytest.mark.asyncio
async def test_extend_claude_aligned_requires_params_keyword():
    """Calling without params= is a TypeError, not a silent fallback."""
    with pytest.raises(TypeError):
        await extend_claude_aligned("hello")  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_extend_claude_aligned_uses_params_model_id_not_registry_pick():
    """The aligned variant must dispatch to params.model_id, even if the
    registry has a 'better' candidate for the prompt."""

    target = "Gemma-4-E4B-it-GGUF"  # an entry that exists in the default registry
    params = InferenceParams(
        model_id=target,
        max_tokens=400,
        prompt_prefix="",
        extra_body={"temperature": 0.6},
    )
    # "ok" is 2 chars (fails >=40 length gate) — but we want this test
    # to assert the *dispatch target* is params.model_id, not the
    # escalation. The test should use a response that's long enough to
    # clear the gate.
    fake_result = (
        "this is a long enough response to clear the length gate",  # text
        0.0,  # cost
        None,  # ttft
        None,  # tps
    )
    with patch("cohezion.inference.fleet._dispatch_one", AsyncMock(return_value=fake_result)):
        result = await extend_claude_aligned("hello", params=params)
    assert result.model == target
    assert result.text == "this is a long enough response to clear the length gate"
    assert result.escalated_to_cloud is False


@pytest.mark.asyncio
async def test_extend_claude_aligned_escalates_on_gate_failure():
    """If the local result is short (length heuristic), escalate to cloud."""
    target = "Gemma-4-E4B-it-GGUF"
    params = InferenceParams(
        model_id=target,
        max_tokens=400,
        prompt_prefix="",
        extra_body={"temperature": 0.6},
    )
    # Local dispatch returns "no" (2 chars) — fails the length gate
    short_local = ("no", 0.0, None, None)
    # Cloud dispatch returns a longer response
    cloud_response = ("this is a much longer cloud response that passes the gate", 0.01, None, None)
    with patch(
        "cohezion.inference.fleet._dispatch_one",
        AsyncMock(side_effect=[short_local, cloud_response]),
    ):
        result = await extend_claude_aligned(
            "hello", params=params, claude_model="claude-sonnet-4-6", max_local_attempts=1
        )
    assert result.escalated_to_cloud is True
    assert result.model == "claude-sonnet-4-6"
