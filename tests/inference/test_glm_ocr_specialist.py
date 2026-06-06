"""Discriminating tests for the GLM-OCR OCR_DOC specialist (2026-06-06, item 23).

Registration is the additive half. id VERIFIED via huggingface_hub.model_info (research round 3):
ggml-org/GLM-OCR-GGUF (official ggml-org repo, 23,009 dl, GGUF + mmproj-GLM-OCR-Q8_0). The
SERVING half is needs-experiment and shares item 18's mmproj/llama-mtmd path + the K1/rule-5 OOM
gate — so verified_working stays False until a real OCR/doc proof passes.

Each test fails a plausible wrong impl:
  - registration that doesn't surface via for_task(OCR_DOC) (the routing entry-point),
  - flipping verified_working=True WITHOUT the mmproj serving proof (PIN test),
  - registering it on a cloud/non-local lane (must be a local $0 lane).
"""

from __future__ import annotations

from cohezion.inference.registry import Lane, Task, get_registry


_GLM_OCR = "GLM-OCR-GGUF"
_LOCAL_LANES = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}


def test_glm_ocr_is_the_ocr_doc_specialist() -> None:
    # Before item 23, for_task(OCR_DOC) was [] (the LAST empty Task slot). Now it returns GLM-OCR.
    ocr = get_registry().for_task(Task.OCR_DOC)
    assert ocr, "OCR_DOC has no specialist — registration did not surface via for_task"
    assert ocr[0].model_id == _GLM_OCR


def test_glm_ocr_registered_but_NOT_yet_verified() -> None:
    # The mmproj serving proof has NOT been run (shares item 18's vision-projector path).
    # verified_working MUST be False until a real OCR/doc proof passes — premature flip fails here.
    entry = get_registry().models.get(_GLM_OCR)
    assert entry is not None
    assert entry.verified_working is False


def test_glm_ocr_is_on_a_local_zero_dollar_lane() -> None:
    entry = get_registry().models[_GLM_OCR]
    assert entry.lane in _LOCAL_LANES
    assert entry.cost_per_1k_input_usd == 0.0
    assert entry.cost_per_1k_output_usd == 0.0
