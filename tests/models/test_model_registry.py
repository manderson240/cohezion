"""Tests for task-aware ModelRegistry (audit §10 remediation + task-aware upgrade, 2026-06-05).

Covers two builds:
  #1 — the Task-enum seam: new members exist, for_task is expressible, EXISTING for_task
       results are unchanged (falsifiable regression guard).
  #5 — get_best_for_task is task-TYPE aware: classify task → FleetRegistry.for_task →
       preferred specialist; fall back to complexity routing; fail-soft.
"""
from __future__ import annotations

from unittest.mock import patch

from cohezion.inference.fractal_metrics import feynman_path_weight
from cohezion.inference.registry import Lane, Task, get_registry
from cohezion.models.model_registry import ModelRegistry, _classify_task


class _FakeDecision:
    def __init__(self, model: str) -> None:
        self.model = model


class _FakeRouter:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def select_model(self, query, max_cost_usd=None, cache_hit_rate=None):
        self.calls.append((query, max_cost_usd, cache_hit_rate))
        return _FakeDecision("complexity-fallback-model"), True


# ---- #1: Task-enum seam (falsifiable regression guard) --------------------------


def test_new_task_members_exist() -> None:
    for name in ("EXTRACTION", "VISION", "FIM", "FUNCTION_CALL", "RERANK", "OCR_DOC"):
        assert hasattr(Task, name)


def test_new_tasks_have_no_models_yet_and_existing_unchanged() -> None:
    reg = get_registry()
    # EXTRACTION/VISION now have the LFM2.5-VL specialist (item 4, 2026-06-06).
    assert reg.for_task(Task.EXTRACTION)[0].model_id == "LFM2.5-VL-1.6B-Extract-GGUF"
    assert any(m.model_id == "LFM2.5-VL-1.6B-Extract-GGUF" for m in reg.for_task(Task.VISION))
    # RERANK now has the Qwen3-Reranker specialist (item 19, 2026-06-06).
    assert reg.for_task(Task.RERANK)[0].model_id == "Qwen3-Reranker-0.6B-GGUF"
    # FUNCTION_CALL now has the Granite-4.1-3b specialist (item 21, 2026-06-06).
    assert reg.for_task(Task.FUNCTION_CALL)[0].model_id == "Granite-4.1-3b-GGUF"
    # The remaining new specialist tasks have no model yet -> empty (not an error).
    for t in (Task.FIM, Task.OCR_DOC):
        assert reg.for_task(t) == []
    # Falsifiable regression guard: existing task buckets are untouched & still coherent.
    reasoning = reg.for_task(Task.REASONING)
    assert len(reasoning) >= 1
    assert all(Task.REASONING in m.task_affinity for m in reasoning)
    # priority-sorted (best first)
    assert [m.priority for m in reasoning] == sorted(m.priority for m in reasoning)


# ---- #5: task classification ----------------------------------------------------


def test_classify_task_keyword_and_direct_mapping() -> None:
    assert _classify_task("extract the invoice fields") == Task.EXTRACTION
    assert _classify_task("write code to refactor this") == Task.CODE_GEN
    assert _classify_task("rerank these chunks") == Task.RERANK
    assert _classify_task("VQA on this image") == Task.VISION
    assert _classify_task("summarize the doc") == Task.SUMMARIZATION
    assert _classify_task("reasoning") == Task.REASONING        # direct value match
    assert _classify_task("xyzzy plugh foobar") is None
    assert _classify_task("") is None


# ---- #5: task-aware selection vs fallback ---------------------------------------


def test_task_aware_returns_registry_specialist_for_known_task() -> None:
    # "reasoning" -> Task.REASONING -> a registry model with REASONING affinity (NOT the
    # complexity router). Discriminates the old behavior that discarded task type.
    fake = _FakeRouter()
    got = ModelRegistry(router=fake).get_best_for_task("reasoning")
    reasoning_ids = {m.model_id for m in get_registry().for_task(Task.REASONING)}
    assert got in reasoning_ids
    assert fake.calls == []  # router NOT consulted when a specialist exists


def test_unregistered_task_falls_back_to_complexity_router() -> None:
    # "ocr this scanned document" classifies to OCR_DOC, which STILL has no specialist ->
    # falls through to the router. Proves classification AND graceful fallback both work.
    # (EXTRACTION is no longer the example here: it now has the LFM specialist — item 4.)
    fake = _FakeRouter()
    got = ModelRegistry(router=fake).get_best_for_task("ocr this scanned document", budget=0.01)
    assert got == "complexity-fallback-model"
    assert fake.calls[0] == ("ocr this scanned document", 0.01, 0.95)


def test_unclassifiable_task_falls_back_to_router() -> None:
    fake = _FakeRouter()
    got = ModelRegistry(router=fake).get_best_for_task("xyzzy plugh foobar", prefer_fast=False)
    assert got == "complexity-fallback-model"
    assert fake.calls[0] == ("xyzzy plugh foobar", None, None)  # prefer_fast=False -> no cache bias


def test_fail_soft_returns_none_on_router_error() -> None:
    # Unclassifiable task reaches the router; a router failure must NOT propagate.
    class _Boom:
        def select_model(self, **kw):
            raise RuntimeError("router down")

    assert ModelRegistry(router=_Boom()).get_best_for_task("xyzzy plugh foobar") is None


def test_no_arg_construction_and_real_routing_integration() -> None:
    result = ModelRegistry().get_best_for_task("analyze this codebase")
    assert result is None or isinstance(result, str)


def test_swarm_service_and_cli_still_import() -> None:
    import importlib

    importlib.import_module("cohezion.services.swarm_service")
    importlib.import_module("cohezion.cli")


# ---- electricity + quality in the routing amplitude -----------------------------


def test_feynman_cc2_preserved_when_no_energy() -> None:
    # CC2 (harness-protected): default energy=0 must be byte-identical to the old behavior.
    assert feynman_path_weight(0.5, 0.0) == 0.5
    assert feynman_path_weight(0.5, 0.0, 0.0) == 0.5
    # the exact CC2 harness invariant still holds (local $0 beats cloud $0.01):
    assert feynman_path_weight(0.5, 0.0) > feynman_path_weight(1.0, 0.01)


def test_feynman_energy_penalizes_more_joules() -> None:
    # Electricity term: more joules → lower amplitude, monotonically.
    a0 = feynman_path_weight(1.0, 0.0, 0.0)
    a_npu = feynman_path_weight(1.0, 0.0, 4.0)    # ~NPU turn
    a_cpu = feynman_path_weight(1.0, 0.0, 55.0)   # ~CPU turn
    assert a0 == 1.0
    assert a0 > a_npu > a_cpu


class _FakeEntry:
    def __init__(self, model_id: str, lane, priority: int) -> None:
        self.model_id = model_id
        self.lane = lane
        self.priority = priority


class _FakeReg:
    def __init__(self, entries: list) -> None:
        self._entries = entries

    def for_task(self, task) -> list:
        return self._entries


def test_electricity_tiebreaks_to_npu_at_equal_priority() -> None:
    # Equal task-fit (priority) → the lower-wattage lane (NPU 2W) wins over CPU (55W).
    entries = [_FakeEntry("cpu-model", Lane.CPU, 10), _FakeEntry("npu-model", Lane.NPU, 10)]
    with patch("cohezion.inference.registry.get_registry", return_value=_FakeReg(entries)):
        got = ModelRegistry().get_best_for_task("reasoning")
    assert got == "npu-model"


def test_quality_beats_electricity_no_watts_override() -> None:
    # Discriminating: a better-FIT CPU model (priority 10) must beat a worse-fit NPU (priority
    # 50) even though the NPU draws far fewer watts. Electricity is a TIE-breaker, NOT an override.
    entries = [_FakeEntry("npu-weak", Lane.NPU, 50), _FakeEntry("cpu-strong", Lane.CPU, 10)]
    with patch("cohezion.inference.registry.get_registry", return_value=_FakeReg(entries)):
        got = ModelRegistry().get_best_for_task("reasoning")
    assert got == "cpu-strong"
