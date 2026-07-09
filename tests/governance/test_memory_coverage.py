"""Discriminating tests for the neuron-memory coverage report (item 55, 2026-06-06).

`memory_coverage(store)` answers "what does the fleet remember?" — per neuron country, the SET of
task classes the fleet has procedural memory for (the observability complement to item-37's per-task
recall). Read-only; operates on an injected store. task_class is read from the neuron's TAGS (not its
name) via a structural-tag denylist (country/label/lane vocab).

Each test fails a plausible wrong impl:
  - misses a task class / leaks a structural-or-lane tag → test_cerebellum_tasks_exact,
  - parses the name instead of the tags → test_reads_tags_not_name,
  - drops a country with no neurons → test_empty_country_is_empty_set,
  - mixes countries → test_cross_country_isolation.
"""

from __future__ import annotations

from cohezion.governance.knowledge_bridge import (
    build_cerebellum_neuron,
    build_skill_neuron,
)
from cohezion.governance.neuron_quality import memory_coverage
from cohezion.models.routing_log import build_inference_neuron


def test_cerebellum_tasks_exact() -> None:
    store = [
        build_cerebellum_neuron("RERANK", "igpu", consistency=1.0, samples=6),
        build_cerebellum_neuron("OCR_DOC", "cpu", consistency=1.0, samples=6),
    ]
    cov = memory_coverage(store)
    assert cov["cerebellum"] == {"RERANK", "OCR_DOC"}  # lane (igpu/cpu) + 'procedural' excluded


def test_reads_tags_not_name() -> None:
    # Name is garbage; the task_class lives only in the tags → must still be covered.
    neuron = {
        "name": "GARBLED",
        "country": "cerebellum",
        "tags": ["cerebellum", "procedural", "ZZZ", "igpu"],
    }
    cov = memory_coverage([neuron])
    assert "ZZZ" in cov["cerebellum"]
    assert "GARBLED" not in cov["cerebellum"]


def test_empty_country_is_empty_set() -> None:
    store = [build_cerebellum_neuron("RERANK", "igpu", consistency=1.0, samples=6)]
    cov = memory_coverage(store)
    assert cov["inference"] == set() and cov["skill"] == set()


def test_cross_country_isolation() -> None:
    store = [
        build_inference_neuron("A", "m", "npu"),
        build_skill_neuron("B", "a distilled skill"),
        build_cerebellum_neuron("C", "cpu", consistency=1.0, samples=6),
    ]
    cov = memory_coverage(store)
    assert cov["inference"] == {"A"}
    assert cov["skill"] == {"B"}
    assert cov["cerebellum"] == {"C"}


def test_empty_store_all_empty() -> None:
    assert memory_coverage([]) == {"inference": set(), "skill": set(), "cerebellum": set()}
