"""Regression guard for F2 Phase 2 (port-bypass triage).

The riskiest finding of the triage: ``fleet._dispatch_one`` selects the API
*flavour* (Ollama ``/api/chat`` vs OpenAI-compatible ``/v1``) from the model's
endpoint via ``model.endpoint.endswith(":11434")`` (``fleet.py`` line ~438).
Phase 2 repointed the deprecated per-lane Lemonade ports (:13306-:13309) at the
:13305 OmniRouter. This test proves that repoint did NOT break flavour
selection: an Ollama :11434 endpoint still dispatches through the Ollama path,
and a :13305 (Lemonade router) endpoint dispatches through the OpenAI-compatible
path. If a blind port swap had touched the discriminator, one of these would
route to the wrong dispatcher.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.inference.fleet import _dispatch_one
from cohezion.inference.registry import Lane, ModelEntry, Task, WeightQuant


def _entry(*, lane: Lane, endpoint: str) -> ModelEntry:
    return ModelEntry(
        model_id="test-model",
        lane=lane,
        endpoint=endpoint,
        runtime_backend="",
        task_affinity=frozenset({Task.GENERAL}),
        weight_quant=WeightQuant.Q4_K_M,
        context_window=8192,
    )


@pytest.mark.asyncio
async def test_ollama_endpoint_dispatches_via_ollama_path() -> None:
    """A CPU-lane :11434 endpoint must select the Ollama dispatcher, not OpenAI."""
    model = _entry(lane=Lane.CPU, endpoint="http://localhost:11434")
    # _dispatch_ollama is unpacked as a 2-tuple; _dispatch_openai_compatible's
    # result is returned directly (4-tuple).
    ollama_mock = AsyncMock(return_value=("ok", 0.0))
    openai_mock = AsyncMock(return_value=("ok", 0.0, None, None))

    with (
        patch("cohezion.inference.fleet._dispatch_ollama", ollama_mock),
        patch("cohezion.inference.fleet._dispatch_openai_compatible", openai_mock),
    ):
        await _dispatch_one(model, "hi", None, 5.0)

    ollama_mock.assert_awaited_once()
    openai_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_router_endpoint_dispatches_via_openai_path() -> None:
    """A :13305 (OmniRouter) endpoint must select the OpenAI-compatible dispatcher.

    This is the exact case Phase 2 introduced by repointing per-lane ports at
    :13305 — it must NOT fall into the Ollama branch.
    """
    model = _entry(lane=Lane.IGPU_ROCWMMA, endpoint="http://localhost:13305")
    ollama_mock = AsyncMock(return_value=("ok", 0.0))
    openai_mock = AsyncMock(return_value=("ok", 0.0, None, None))

    with (
        patch("cohezion.inference.fleet._dispatch_ollama", ollama_mock),
        patch("cohezion.inference.fleet._dispatch_openai_compatible", openai_mock),
    ):
        await _dispatch_one(model, "hi", None, 5.0)

    openai_mock.assert_awaited_once()
    ollama_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_cpu_lane_router_endpoint_is_not_treated_as_ollama() -> None:
    """The discriminator is endpoint-based, not lane-based: a CPU-lane model on
    the :13305 router (as Gemma-4-31B now is) must dispatch OpenAI-compatible."""
    model = _entry(lane=Lane.CPU, endpoint="http://localhost:13305")
    ollama_mock = AsyncMock(return_value=("ok", 0.0))
    openai_mock = AsyncMock(return_value=("ok", 0.0, None, None))

    with (
        patch("cohezion.inference.fleet._dispatch_ollama", ollama_mock),
        patch("cohezion.inference.fleet._dispatch_openai_compatible", openai_mock),
    ):
        await _dispatch_one(model, "hi", None, 5.0)

    openai_mock.assert_awaited_once()
    ollama_mock.assert_not_awaited()
