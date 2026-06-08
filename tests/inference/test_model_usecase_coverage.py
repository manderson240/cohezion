"""Discriminating tests for model_usecase_coverage (backlog item 98, 2026-06-08).

`model_usecase_coverage(served_models, registry)` is the INVERSE of item-62 coverage_gaps: it flags
served fleet models with NO Task affinity ("earns no routing slot"). A served model with no registry
entry, OR an entry with empty task_affinity, is `no_usecase`. Report-only, pure over injected models
+ a real FleetRegistry.

Each test fails a plausible wrong impl:
  - an impl that iterates the REGISTRY (not served_models) misses an unregistered served model
    → test_unregistered_served_model_flagged,
  - an impl that treats any registry entry as covered → test_empty_affinity_flagged,
  - an impl that flags a model WITH affinity → test_model_with_affinity_covered.
"""

from __future__ import annotations

import copy

from cohezion.inference.local_coverage import model_usecase_coverage
from cohezion.inference.registry import FleetRegistry, get_registry


def _isolated_registry() -> FleetRegistry:
    return FleetRegistry(models=copy.deepcopy(get_registry().models))


def _a_registered_model_id(reg: FleetRegistry) -> str:
    # A model that genuinely has a Task affinity (every default entry does).
    return next(m.model_id for m in reg.models.values() if m.task_affinity)


def test_model_with_affinity_covered() -> None:
    reg = _isolated_registry()
    mid = _a_registered_model_id(reg)
    assert model_usecase_coverage([mid], reg) == []  # has affinity → covered → not flagged


def test_unregistered_served_model_flagged() -> None:
    # DISCRIMINATING: a served model with NO registry entry is no_usecase. An impl that iterates the
    # registry (not served_models) would never see it.
    reg = _isolated_registry()
    assert model_usecase_coverage(["a-model-not-in-the-registry"], reg) == [
        "a-model-not-in-the-registry"
    ]


def test_empty_affinity_flagged() -> None:
    # DISCRIMINATING: a registered model with EMPTY task_affinity is no_usecase. An impl that treats
    # "has a registry entry" as covered would wrongly clear it.
    reg = _isolated_registry()
    mid = _a_registered_model_id(reg)
    reg.models[mid].task_affinity = frozenset()  # zero its affinity
    assert model_usecase_coverage([mid], reg) == [mid]


def test_mixed_partition() -> None:
    reg = _isolated_registry()
    covered = _a_registered_model_id(reg)
    out = model_usecase_coverage([covered, "ghost-model"], reg)
    assert out == ["ghost-model"]  # only the unregistered one flagged


def test_empty_served_models() -> None:
    assert model_usecase_coverage([], _isolated_registry()) == []


def test_result_deduped_and_sorted() -> None:
    reg = _isolated_registry()
    out = model_usecase_coverage(["z-ghost", "a-ghost", "z-ghost"], reg)
    assert out == ["a-ghost", "z-ghost"]  # sorted, de-duplicated


def test_live_registry_known_model_covered() -> None:
    # Non-fabricated: against the REAL registry, a genuinely-registered model is covered.
    reg = get_registry()
    mid = _a_registered_model_id(reg)
    assert mid not in model_usecase_coverage([mid, "definitely-not-served"], reg)
