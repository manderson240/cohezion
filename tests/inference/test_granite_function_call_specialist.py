"""Discriminating tests for the Granite-4.1-3b FUNCTION_CALL specialist (2026-06-06, item 21).

Registration is the additive half. The SERVING half is needs-experiment: llama.cpp tool-calling
breaks when the orchestrator's prompt format doesn't match the model's chat template / tool-call
special tokens — so verified_working stays False until a real `finish_reason=tool_calls` proof
with valid args passes. Same validated no-thinking, tool-capable Granite family as Hermes's main
model (Granite-4.1-8B), but small enough for a $0 local specialist.

Each test fails a plausible wrong impl:
  - registration that doesn't surface via for_task(FUNCTION_CALL) (the routing entry-point),
  - flipping verified_working=True WITHOUT the tool-call proof (PIN test catches a premature flip),
  - registering it on a cloud/non-local lane (must be a local $0 lane).
"""

from __future__ import annotations

from cohezion.inference.registry import Lane, Task, get_registry


_GRANITE = "Granite-4.1-3b-GGUF"
_LOCAL_LANES = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}


def test_granite_is_the_function_call_specialist() -> None:
    # Before item 21, for_task(FUNCTION_CALL) was []. Now it must return the Granite entry first.
    fc = get_registry().for_task(Task.FUNCTION_CALL)
    assert fc, "FUNCTION_CALL has no specialist — registration did not surface via for_task"
    assert fc[0].model_id == _GRANITE


def test_granite_registered_but_NOT_yet_verified() -> None:
    # The tool-call proof has NOT been run. verified_working MUST be False until a real
    # finish_reason=tool_calls proof with valid args passes — a premature flip fails here.
    entry = get_registry().models.get(_GRANITE)
    assert entry is not None
    assert entry.verified_working is False


def test_granite_is_on_a_local_zero_dollar_lane() -> None:
    entry = get_registry().models[_GRANITE]
    assert entry.lane in _LOCAL_LANES
    assert entry.cost_per_1k_input_usd == 0.0
    assert entry.cost_per_1k_output_usd == 0.0
