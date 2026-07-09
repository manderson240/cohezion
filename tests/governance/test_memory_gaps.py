"""Discriminating tests for memory_gaps (backlog item 75, 2026-06-07).

The actionable complement to item-55 `memory_coverage`: per neuron country, WHICH task classes
the fleet handles but has NO procedural memory for (`wanted - covered`). Composes
`memory_coverage` + an injected task-class set. Report-only, pure.

Each test fails a plausible wrong impl:
  - an impl that returns coverage instead of its complement → test_partial_coverage_gap,
  - an impl that returns {} (no countries) on an empty store → test_empty_store_all_gaps,
  - an impl that leaves residual gaps under full coverage → test_full_coverage_empty.
"""

from __future__ import annotations

from cohezion.governance.neuron_quality import memory_gaps


_TASKS = {"TASK_A", "TASK_B", "TASK_C"}


def _cereb(task: str) -> dict:
    # a cerebellum neuron whose tags cover one task class (country tag is structural, dropped).
    return {"country": "cerebellum", "tags": ["cerebellum", task]}


def test_partial_coverage_gap() -> None:
    gaps = memory_gaps([_cereb("TASK_A")], task_classes=_TASKS)
    assert gaps["cerebellum"] == {"TASK_B", "TASK_C"}  # covered A → gap is the rest
    assert gaps["inference"] == _TASKS  # nothing in inference → all are gaps
    assert gaps["skill"] == _TASKS


def test_full_coverage_empty() -> None:
    store = [_cereb("TASK_A"), _cereb("TASK_B"), _cereb("TASK_C")]
    assert memory_gaps(store, task_classes=_TASKS)["cerebellum"] == set()


def test_empty_store_all_gaps() -> None:
    gaps = memory_gaps([], task_classes={"TASK_A", "TASK_B"})
    # every country present, each missing everything (NOT an empty dict).
    assert gaps == {
        "cerebellum": {"TASK_A", "TASK_B"},
        "inference": {"TASK_A", "TASK_B"},
        "skill": {"TASK_A", "TASK_B"},
    }
