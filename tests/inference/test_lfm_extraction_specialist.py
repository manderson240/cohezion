"""Discriminating tests for the LFM2.5-VL extraction specialist (2026-06-06, item 4).

Registration is the additive half (the mmproj proof is needs-experiment — see
docs/research/LFM_VL_EXTRACTION_2026-06-06.md). Each test fails a plausible wrong impl:
  - registration that doesn't actually surface via for_task(EXTRACTION) (the routing entry-point),
  - marking the model verified_working=True WITHOUT having run the mmproj experiment
    (the test PINS verified=False so a premature flip is caught),
  - registering it on a cloud/non-local lane (it must be a local $0 lane).
"""

from __future__ import annotations

from cohezion.inference.registry import Lane, Task, get_registry


_LFM = "LFM2.5-VL-1.6B-Extract-GGUF"
_LOCAL_LANES = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}


def test_lfm_is_the_extraction_specialist() -> None:
    # Before item 4, for_task(EXTRACTION) was []. Now it must return the LFM entry first.
    ex = get_registry().for_task(Task.EXTRACTION)
    assert ex, "EXTRACTION has no specialist — registration did not surface via for_task"
    assert ex[0].model_id == _LFM


def test_lfm_also_serves_vision() -> None:
    vis = {m.model_id for m in get_registry().for_task(Task.VISION)}
    assert _LFM in vis


def test_lfm_registered_but_NOT_yet_verified() -> None:
    # The mmproj experiment has NOT been run (model not downloaded). verified_working MUST be
    # False until a real image-extraction proof passes — a premature flip to True fails here.
    entry = get_registry().models.get(_LFM)
    assert entry is not None
    assert entry.verified_working is False


def test_lfm_is_on_a_local_zero_dollar_lane() -> None:
    entry = get_registry().models[_LFM]
    assert entry.lane in _LOCAL_LANES
    assert entry.cost_per_1k_input_usd == 0.0
