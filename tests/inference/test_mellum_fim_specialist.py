"""Discriminating tests for the Mellum FIM specialist (2026-06-06, item 28).

Registration is the additive half. id VERIFIED via huggingface_hub.model_info (research round 4):
JetBrains/Mellum-4b-base-gguf (406 dl, 1 GGUF mellum-4b-base.Q8_0.gguf). The SERVING half is
needs-experiment (FIM-completion via /api/v1/completions with <fim_*> tokens) — so
verified_working stays False until a real FIM proof passes.

Each test fails a plausible wrong impl:
  - registration that doesn't surface via for_task(FIM) (the routing entry-point),
  - flipping verified_working=True WITHOUT the FIM serving proof (PIN test),
  - registering it on a cloud/non-local lane (must be a local $0 lane),
  - the item-28 closure check: FIM was the LAST empty slot, so ALL 6 specialist slots are now
    filled (an impl that registered FIM on the wrong task would leave FIM empty + fail here).
"""

from __future__ import annotations

from cohezion.inference.registry import Lane, Task, get_registry


_MELLUM = "Mellum-4b-base-GGUF"
_LOCAL_LANES = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}


def test_mellum_is_the_fim_specialist() -> None:
    # Before item 28, for_task(FIM) was [] (the LAST empty Task slot). Now it returns Mellum.
    fim = get_registry().for_task(Task.FIM)
    assert fim, "FIM has no specialist — registration did not surface via for_task"
    assert fim[0].model_id == _MELLUM


def test_mellum_registered_but_NOT_yet_verified() -> None:
    # The FIM-completion serving proof has NOT been run. verified_working MUST be False until a
    # real <fim_*> /api/v1/completions proof passes — a premature flip fails here.
    entry = get_registry().models.get(_MELLUM)
    assert entry is not None
    assert entry.verified_working is False


def test_mellum_is_on_a_local_zero_dollar_lane() -> None:
    entry = get_registry().models[_MELLUM]
    assert entry.lane in _LOCAL_LANES
    assert entry.cost_per_1k_input_usd == 0.0
    assert entry.cost_per_1k_output_usd == 0.0


def test_all_six_specialist_slots_now_filled() -> None:
    # Item-28 closure: FIM was the last empty slot. Every specialist Task must now have a model.
    reg = get_registry()
    for task in (
        Task.EXTRACTION,
        Task.VISION,
        Task.FIM,
        Task.FUNCTION_CALL,
        Task.RERANK,
        Task.OCR_DOC,
    ):
        assert reg.for_task(task), f"specialist slot {task.name} unexpectedly empty"
