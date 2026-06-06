"""Discriminating tests for the Qwen3-Reranker RERANK specialist (2026-06-06, item 19).

Registration is the additive half. The SERVING half is needs-experiment: llama.cpp GGUF
rerankers require `--pooling rank` + a proper `convert_hf_to_gguf.py` conversion, and the
well-known failure mode is degenerate near-zero scores (~4.5e-23) for every pair — see
docs/research/BLEEDING_EDGE_FEED.md round 1. So verified_working stays False until a real
non-degenerate /v1/rerank proof passes.

Each test fails a plausible wrong impl:
  - registration that doesn't actually surface via for_task(RERANK) (the routing entry-point),
  - marking the model verified_working=True WITHOUT having run the /v1/rerank proof
    (the test PINS verified=False so a premature flip — shipping the 4.5e-23 trap — is caught),
  - registering it on a cloud/non-local lane (it must be a local $0 lane).
"""

from __future__ import annotations

from cohezion.inference.registry import Lane, Task, get_registry


_RERANKER = "Qwen3-Reranker-0.6B-GGUF"
_LOCAL_LANES = {Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU}


def test_qwen3_reranker_is_the_rerank_specialist() -> None:
    # Before item 19, for_task(RERANK) was []. Now it must return the reranker entry first.
    rr = get_registry().for_task(Task.RERANK)
    assert rr, "RERANK has no specialist — registration did not surface via for_task"
    assert rr[0].model_id == _RERANKER


def test_qwen3_reranker_registered_but_NOT_yet_verified() -> None:
    # The /v1/rerank proof has NOT been run (model not converted/served). verified_working MUST
    # be False until a real NON-DEGENERATE score proof passes — a premature flip to True (which
    # would route live rerank traffic into the 4.5e-23 degenerate-score trap) fails here.
    entry = get_registry().models.get(_RERANKER)
    assert entry is not None
    assert entry.verified_working is False


def test_qwen3_reranker_is_on_a_local_zero_dollar_lane() -> None:
    entry = get_registry().models[_RERANKER]
    assert entry.lane in _LOCAL_LANES
    assert entry.cost_per_1k_input_usd == 0.0
    assert entry.cost_per_1k_output_usd == 0.0
