"""RED tests for the card-aligned execute_fn with datamesh hooks (PR 1).

The aligned execute_fn is the seam that wires the WS1+WS2
card-aligned local-fleet surface into the compound loop. It
also feeds evidence back into the datamesh (Connections A, D, E).

Contracts:
- The function is async-callable: `await execute_fn_aligned(guidance)`
  returns `(text, metrics)`.
- It calls `route_by_capability` to pick a (ModelEntry, InferenceParams)
  pair from the registry.
- It calls `extend_claude_aligned` (the WS2A function) with the params
  from the router. NOT a registry-pick: the params lock the dispatch.
- It preflights `ResourceGuard.can_load_model(0)` (soft gate) and acquires
  `FleetLock` for the duration.
- It emits a `WITNESS_MARK` precipitation event with a 12D point derived
  from the card + outcome. A per-(task, model) cooldown of 1/hour is
  enforced to keep the bus a firehose, not a flood.
- It writes a vault note `EXEC-<timestamp>-<slug>.md` per execution.
- It fires-and-forgets a SurrealDB upsert to `fleet_research:execution`.
- On failure, it returns the error as `(text, metrics)` with
  `metrics["card_aligned"] = False` and an `error` field; the function
  never raises (the compound loop expects `(text, metrics)` always).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.inference.model_card_harness import InferenceParams


# ── The seam: returns (text, metrics) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_aligned_execute_fn_returns_text_and_metrics():
    """The aligned execute_fn returns the (text, metrics) tuple shape
    the CompoundExecutor expects."""
    from cohezion.compound.execute_fn_aligned import execute_fn_aligned

    guidance = {"task_description": "summarize this", "operation_type": "summarize"}
    fake_text = "this is a real summary that is long enough to pass the gate"
    fake_params = InferenceParams(
        model_id="Gemma-4-E4B-it-GGUF", max_tokens=400, prompt_prefix="", extra_body={}
    )
    fake_entry = _make_entry_with_profile("Gemma-4-E4B-it-GGUF")
    with (
        patch(
            "cohezion.compound.execute_fn_aligned.route_by_capability",
            return_value=(fake_entry, fake_params),
        ),
        patch("cohezion.compound.execute_fn_aligned.FleetLock") as mock_lock_cls,
        patch(
            "cohezion.compound.execute_fn_aligned.extend_claude_aligned",
            new=AsyncMock(
                return_value=_RouteResult(
                    text=fake_text, model="Gemma-4-E4B-it-GGUF", lane="igpu", error=None
                )
            ),
        ),
    ):
        mock_lock = MagicMock()
        mock_lock.acquire = MagicMock(return_value=_FakeAsyncCM())
        mock_lock_cls.return_value = mock_lock
        text, metrics = await execute_fn_aligned(guidance)
    assert text == fake_text
    assert isinstance(metrics, dict)
    assert metrics["card_aligned"] is True
    assert metrics["recipe_params_id"] == "Gemma-4-E4B-it-GGUF"


@pytest.mark.asyncio
async def test_aligned_execute_fn_uses_route_by_capability_params():
    """The dispatch uses the params from the router, NOT a fresh registry pick."""
    from cohezion.compound.execute_fn_aligned import execute_fn_aligned

    target_model = "qwen3-coder:30b"
    target_params = InferenceParams(
        model_id=target_model,
        max_tokens=600,
        prompt_prefix="/no_think\n",
        extra_body={"temperature": 0.2},
    )
    fake_result = _RouteResult(
        text="the aligned dispatch went to qwen3-coder as instructed",
        model=target_model,
        lane="cpu",
        error=None,
    )
    fake_entry = _make_entry_with_profile(target_model)
    with (
        patch(
            "cohezion.compound.execute_fn_aligned.route_by_capability",
            return_value=(fake_entry, target_params),
        ) as mock_route,
        patch("cohezion.compound.execute_fn_aligned.FleetLock") as mock_lock_cls,
        patch(
            "cohezion.compound.execute_fn_aligned.extend_claude_aligned",
            new=AsyncMock(return_value=fake_result),
        ) as mock_dispatch,
    ):
        mock_lock = MagicMock()
        mock_lock.acquire = MagicMock(return_value=_FakeAsyncCM())
        mock_lock_cls.return_value = mock_lock
        _text, _metrics = await execute_fn_aligned(
            {"task_description": "refactor function X", "operation_type": "transform"}
        )
    mock_route.assert_called_once()
    # The dispatch went to the target model, not a registry alternative
    mock_dispatch.assert_called_once()
    call_kwargs = mock_dispatch.call_args.kwargs
    assert call_kwargs["params"].model_id == target_model
    assert call_kwargs["params"].prompt_prefix == "/no_think\n"


# ── Pre-flight: ResourceGuard + FleetLock ────────────────────────────────────


@pytest.mark.asyncio
async def test_aligned_execute_fn_preflights_resource_guard():
    """The function preflights ResourceGuard.can_load_model(0) before dispatch."""
    from cohezion.compound.execute_fn_aligned import execute_fn_aligned

    fake_params = InferenceParams(model_id="x", max_tokens=400, extra_body={})
    fake_entry = _make_entry_with_profile("x")
    with (
        patch(
            "cohezion.compound.execute_fn_aligned.route_by_capability",
            return_value=(fake_entry, fake_params),
        ),
        patch("cohezion.compound.execute_fn_aligned.ResourceGuard") as mock_rg,
        patch("cohezion.compound.execute_fn_aligned.FleetLock") as mock_lock_cls,
        patch(
            "cohezion.compound.execute_fn_aligned.extend_claude_aligned",
            new=AsyncMock(return_value=_RouteResult(text="ok", model="x", lane="x", error=None)),
        ),
    ):
        mock_lock = MagicMock()
        mock_lock.acquire = MagicMock(return_value=_FakeAsyncCM())
        mock_lock_cls.return_value = mock_lock
        await execute_fn_aligned({"task_description": "x", "operation_type": "analyze"})
    mock_rg.return_value.can_load_model.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_aligned_execute_fn_acquires_fleet_lock_for_duration():
    """The function acquires FleetLock for the duration of the dispatch."""
    from cohezion.compound.execute_fn_aligned import execute_fn_aligned

    fake_params = InferenceParams(model_id="x", max_tokens=400, extra_body={})
    fake_entry = _make_entry_with_profile("x")
    with (
        patch(
            "cohezion.compound.execute_fn_aligned.route_by_capability",
            return_value=(fake_entry, fake_params),
        ),
        patch("cohezion.compound.execute_fn_aligned.FleetLock") as mock_lock_cls,
        patch(
            "cohezion.compound.execute_fn_aligned.extend_claude_aligned",
            new=AsyncMock(return_value=_RouteResult(text="ok", model="x", lane="x", error=None)),
        ),
    ):
        # The FleetLock is used as `async with FleetLock().acquire(key, timeout)`.
        # `acquire` must be an async context manager; build a fake one.
        mock_lock = MagicMock()
        mock_lock.acquire = MagicMock(return_value=_FakeAsyncCM())
        mock_lock_cls.return_value = mock_lock
        await execute_fn_aligned({"task_description": "x", "operation_type": "analyze"})
    mock_lock.acquire.assert_called_once()
    call = mock_lock.acquire.call_args
    # The lock key mentions the params model_id so two consumers serialize
    assert "fleet_lock:modelload" in str(call)


# ── Connection A: WITNESS_MARK with 12D point from the card ──────────────────


@pytest.mark.asyncio
async def test_aligned_execute_fn_emits_witness_mark_with_12d_from_card():
    """A WITNESS_MARK precipitation event is emitted on every successful
    aligned execution, with a 12D point derived from the card."""
    from cohezion.compound import execute_fn_aligned as mod
    from cohezion.compound.execute_fn_aligned import execute_fn_aligned

    # Reset the cooldown so this test is independent of prior tests
    mod._witness_cooldown.clear()

    fake_params = InferenceParams(model_id="Gemma-4-E4B-it-GGUF", max_tokens=400, extra_body={})
    fake_entry = _make_entry_with_profile("Gemma-4-E4B-it-GGUF")
    with (
        patch(
            "cohezion.compound.execute_fn_aligned.route_by_capability",
            return_value=(fake_entry, fake_params),
        ),
        patch("cohezion.compound.execute_fn_aligned.FleetLock") as mock_lock_cls,
        patch(
            "cohezion.compound.execute_fn_aligned.extend_claude_aligned",
            new=AsyncMock(
                return_value=_RouteResult(
                    text="ok", model="Gemma-4-E4B-it-GGUF", lane="igpu", error=None
                )
            ),
        ),
        patch("cohezion.compound.execute_fn_aligned.bus") as mock_bus,
    ):
        mock_lock = MagicMock()
        mock_lock.acquire = MagicMock(return_value=_FakeAsyncCM())
        mock_lock_cls.return_value = mock_lock
        await execute_fn_aligned({"task_description": "x", "operation_type": "analyze"})
    mock_bus.emit.assert_called_once()
    event = mock_bus.emit.call_args.args[0]
    # The event is a WITNESS_MARK
    from cohezion.precipitation.events import PrecipitationKind

    assert event.kind == PrecipitationKind.WITNESS_MARK
    # The 12D point has a non-baseline value on the family fingerprint
    twelve_d = event.twelve_d
    assert twelve_d["logic"] == 0.7  # gemma4 → logic
    # Coherence reflects the success outcome
    assert event.coherence == 0.6


@pytest.mark.asyncio
async def test_witness_mark_cooldown_per_task_and_model():
    """A second call within the same hour for the same (task, model) is
    suppressed. The bus sees the first call but not the second."""
    from cohezion.compound import execute_fn_aligned as mod
    from cohezion.compound.execute_fn_aligned import execute_fn_aligned

    # Reset the cooldown cache so this test is independent
    mod._witness_cooldown.clear()

    fake_params = InferenceParams(model_id="Gemma-4-E4B-it-GGUF", max_tokens=400, extra_body={})
    fake_entry = _make_entry_with_profile("Gemma-4-E4B-it-GGUF")
    with (
        patch(
            "cohezion.compound.execute_fn_aligned.route_by_capability",
            return_value=(fake_entry, fake_params),
        ),
        patch("cohezion.compound.execute_fn_aligned.FleetLock") as mock_lock_cls,
        patch(
            "cohezion.compound.execute_fn_aligned.extend_claude_aligned",
            new=AsyncMock(
                return_value=_RouteResult(
                    text="ok", model="Gemma-4-E4B-it-GGUF", lane="igpu", error=None
                )
            ),
        ),
        patch("cohezion.compound.execute_fn_aligned.bus") as mock_bus,
    ):
        mock_lock = MagicMock()
        mock_lock.acquire = MagicMock(return_value=_FakeAsyncCM())
        mock_lock_cls.return_value = mock_lock
        # First call: emit
        await execute_fn_aligned({"task_description": "x", "operation_type": "analyze"})
        # Second call within the same hour: suppress
        await execute_fn_aligned({"task_description": "x", "operation_type": "analyze"})
    assert mock_bus.emit.call_count == 1


# ── Connection E: vault note per execution ──────────────────────────────────


@pytest.mark.asyncio
async def test_aligned_execute_fn_writes_vault_note(tmp_path):
    """A vault note `EXEC-<timestamp>-<slug>.md` is written to the vault
    root for every successful aligned execution."""
    from cohezion.compound.execute_fn_aligned import execute_fn_aligned

    fake_params = InferenceParams(model_id="Gemma-4-E4B-it-GGUF", max_tokens=400, extra_body={})
    fake_entry = _make_entry_with_profile("Gemma-4-E4B-it-GGUF")
    with (
        patch(
            "cohezion.compound.execute_fn_aligned.route_by_capability",
            return_value=(fake_entry, fake_params),
        ),
        patch("cohezion.compound.execute_fn_aligned.FleetLock") as mock_lock_cls,
        patch(
            "cohezion.compound.execute_fn_aligned.extend_claude_aligned",
            new=AsyncMock(
                return_value=_RouteResult(
                    text="ok", model="Gemma-4-E4B-it-GGUF", lane="igpu", error=None
                )
            ),
        ),
        patch.dict("os.environ", {"COHEZION_VAULT_ROOT": str(tmp_path)}),
    ):
        mock_lock = MagicMock()
        mock_lock.acquire = MagicMock(return_value=_FakeAsyncCM())
        mock_lock_cls.return_value = mock_lock
        await execute_fn_aligned({"task_description": "x", "operation_type": "analyze"})
    notes = list(tmp_path.glob("EXEC/*/EXEC-*.md"))
    assert len(notes) == 1
    body = notes[0].read_text()
    assert "Gemma-4-E4B-it-GGUF" in body


@pytest.mark.asyncio
async def test_aligned_execute_fn_upserts_surreal_row():
    """A SurrealDB row `fleet_research:execution` is upserted via
    fire-and-forget asyncio.create_task. The function returns
    immediately; the upsert completes in the background."""
    from cohezion.compound.execute_fn_aligned import execute_fn_aligned

    fake_params = InferenceParams(model_id="Gemma-4-E4B-it-GGUF", max_tokens=400, extra_body={})
    fake_entry = _make_entry_with_profile("Gemma-4-E4B-it-GGUF")
    with (
        patch(
            "cohezion.compound.execute_fn_aligned.route_by_capability",
            return_value=(fake_entry, fake_params),
        ),
        patch("cohezion.compound.execute_fn_aligned.FleetLock") as mock_lock_cls,
        patch(
            "cohezion.compound.execute_fn_aligned.extend_claude_aligned",
            new=AsyncMock(
                return_value=_RouteResult(
                    text="ok", model="Gemma-4-E4B-it-GGUF", lane="igpu", error=None
                )
            ),
        ),
        patch(
            "cohezion.compound.execute_fn_aligned._upsert_surreal_execution", new=AsyncMock()
        ) as mock_upsert,
        patch("cohezion.compound.execute_fn_aligned.asyncio.create_task") as mock_create_task,
    ):
        mock_lock = MagicMock()
        mock_lock.acquire = MagicMock(return_value=_FakeAsyncCM())
        mock_lock_cls.return_value = mock_lock
        await execute_fn_aligned({"task_description": "x", "operation_type": "analyze"})
    # The upsert function was scheduled via create_task (fire-and-forget)
    mock_create_task.assert_called_once()
    # The create_task received the result of calling mock_upsert (a
    # coroutine from the AsyncMock). Verify the function was called
    # with the right execution context by checking call_args.
    call_args = mock_create_task.call_args
    # The first positional arg is the coroutine; the underlying mock is
    # the call to mock_upsert. We assert the call pattern instead.
    assert mock_upsert.call_count == 1
    # Close the coroutine to avoid the "coroutine was never awaited" warning
    coro = call_args.args[0]
    if asyncio.iscoroutine(coro):
        coro.close()


@pytest.mark.asyncio
async def test_aligned_execute_fn_returns_error_tuple_on_dispatch_failure():
    """A failed dispatch returns (error_text, metrics) with
    card_aligned=False. The compound loop never sees an exception."""
    from cohezion.compound.execute_fn_aligned import execute_fn_aligned

    fake_params = InferenceParams(model_id="Gemma-4-E4B-it-GGUF", max_tokens=400, extra_body={})
    fake_entry = _make_entry_with_profile("Gemma-4-E4B-it-GGUF")
    with (
        patch(
            "cohezion.compound.execute_fn_aligned.route_by_capability",
            return_value=(fake_entry, fake_params),
        ),
        patch("cohezion.compound.execute_fn_aligned.FleetLock") as mock_lock_cls,
        patch(
            "cohezion.compound.execute_fn_aligned.extend_claude_aligned",
            new=AsyncMock(side_effect=RuntimeError("upstream down")),
        ),
    ):
        mock_lock = MagicMock()
        mock_lock.acquire = MagicMock(return_value=_FakeAsyncCM())
        mock_lock_cls.return_value = mock_lock
        text, metrics = await execute_fn_aligned(
            {"task_description": "x", "operation_type": "analyze"}
        )
    assert "error" in metrics
    assert metrics["card_aligned"] is False
    assert "Error" in text


# ── Helpers ──────────────────────────────────────────────────────────────────


@dataclass
class _RouteResult:
    text: str
    model: str
    lane: str
    error: str | None = None


class _FakeAsyncCM:
    """Async context manager stand-in for FleetLock().acquire(key, timeout)."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_entry_with_profile(model_id: str = "x", family: str = "gemma4"):
    """A ModelEntry-like object that satisfies RecipeGuard.assert_card_present."""
    from cohezion.inference.capability_profile import CapabilityProfile
    from cohezion.inference.registry import Lane

    profile = CapabilityProfile(
        model_id=model_id,
        family=family,
        supported_modes=frozenset({"chat"}),
        optimal_ctx=8192,
        min_ctx=512,
        strengths=frozenset({"code"}),
        weaknesses=frozenset(),
        sampling_sweet_spot={"temperature": 0.6},
        prompt_template_fingerprint="chatml",
        thinking_mode="never",
        known_failure_modes=(),
        source_url="https://example.com",
        read_at=datetime(2026, 6, 4, tzinfo=UTC),
    )
    entry = MagicMock()
    entry.profile = profile
    entry.lane = Lane.IGPU_UNIFIED
    return entry
