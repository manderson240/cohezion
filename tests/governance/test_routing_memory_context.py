"""Discriminating tests for recall-augmented routing context (item 37, 2026-06-06).

`routing_memory_context(task_class, store)` composes item-29 recall_neurons across all three
neuron countries (inference/skill/cerebellum) into one advisory dict. Report-only.

Each test fails a plausible wrong impl:
  - drop a country / not always return all three keys → T_keys,
  - leak a populated country into the empty one (ignore per-country filtering) → T_two_of_three,
  - ignore the task_class key (return another task's neurons) → T_keyfilter,
  - read the real graph when store=None under pytest → T_no_graph.
"""

from __future__ import annotations

from cohezion.governance.knowledge_bridge import (
    deposit_cerebellum_neuron,
    deposit_skill_neuron,
    routing_memory_context,
)
from cohezion.models.routing_log import deposit_inference_neuron


def _stable(task: str, lane: str = "igpu", n: int = 6) -> list[dict]:
    return [{"task_class": task, "lane": lane, "fell_back": False} for _ in range(n)]


def _three_country_store(task: str) -> list[dict]:
    store: list[dict] = []
    deposit_inference_neuron(
        {
            "task_class": task,
            "chosen_model": "m",
            "lane": "igpu",
            "fell_back": False,
            "reward": 1.0,
        },
        store=store,
    )
    deposit_skill_neuron(task, "a distilled skill", gate_passed=True, store=store)
    deposit_cerebellum_neuron(_stable(task), store=store)
    return store


def test_always_returns_exactly_three_country_keys() -> None:
    ctx = routing_memory_context("RERANK", store=[])
    assert set(ctx) == {"inference", "skill", "cerebellum"}


def test_all_three_countries_populated() -> None:
    store = _three_country_store("RERANK")
    ctx = routing_memory_context("RERANK", store=store)
    assert len(ctx["inference"]) == 1
    assert len(ctx["skill"]) == 1
    assert len(ctx["cerebellum"]) == 1


def test_two_of_three_populated_third_empty() -> None:
    # skill + cerebellum present, inference absent → inference must be [], the others non-empty.
    store: list[dict] = []
    deposit_skill_neuron("RERANK", "s", gate_passed=True, store=store)
    deposit_cerebellum_neuron(_stable("RERANK"), store=store)
    ctx = routing_memory_context("RERANK", store=store)
    assert ctx["skill"] and ctx["cerebellum"]
    assert ctx["inference"] == []  # a wrong impl that leaks across countries fails here


def test_no_neurons_all_empty() -> None:
    ctx = routing_memory_context("RERANK", store=[])
    assert ctx == {"inference": [], "skill": [], "cerebellum": []}


def test_filters_by_task_class_key() -> None:
    # A cerebellum neuron for a DIFFERENT task must not appear in this task's context.
    store: list[dict] = []
    deposit_cerebellum_neuron(_stable("OCR_DOC"), store=store)
    ctx = routing_memory_context("RERANK", store=store)
    assert ctx["cerebellum"] == []  # OCR_DOC's neuron is not RERANK's


def test_store_none_under_pytest_reads_no_real_graph() -> None:
    # store=None + under pytest → recall_neurons short-circuits to [] before any graph access.
    ctx = routing_memory_context("RERANK", store=None)
    assert ctx == {"inference": [], "skill": [], "cerebellum": []}
