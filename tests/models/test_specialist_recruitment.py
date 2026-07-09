"""Discriminating tests for Hebbian specialist recruitment (2026-06-06, item 14).

Enriches item-9's chronic-fallback signal into a CONCRETE, human-gated specialist proposal
(task class + suggested lane + rationale). Proposes, NEVER auto-registers. Each test fails a
plausible wrong impl:
  - one that proposes a specialist for a HEALTHY task class,
  - one that auto-registers into the FleetRegistry (it must only PROPOSE),
  - one that suggests a heavy CPU lane for a light routing task (wrong lane heuristic),
  - one that proposes from an empty corpus.
"""

from __future__ import annotations

from cohezion.inference.registry import get_registry
from cohezion.models.routing_log import (
    SpecialistProposal,
    propose_specialists,
)


def _recs(task_class: str, n: int, fallbacks: int) -> list[dict]:
    return [
        {"task_class": task_class, "chosen_model": "m", "lane": "", "fell_back": i < fallbacks}
        for i in range(n)
    ]


def test_chronic_fallback_yields_concrete_proposal() -> None:
    props = propose_specialists(_recs("EXTRACTION", 10, 8))
    assert len(props) == 1
    p = props[0]
    assert isinstance(p, SpecialistProposal)
    assert p.task_class == "EXTRACTION"
    assert p.suggested_lane in {"igpu_rocwmma", "igpu_unified"}  # extraction → iGPU, not CPU
    assert p.fallback_rate == 0.8


def test_routing_task_suggests_npu_lane() -> None:
    # A light classification/routing task should recruit onto the cheap NPU lane.
    props = propose_specialists(_recs("ROUTING", 10, 9))
    assert props and props[0].suggested_lane == "npu"


def test_reasoning_task_suggests_cpu_lane() -> None:
    props = propose_specialists(_recs("REASONING", 10, 9))
    assert props and props[0].suggested_lane == "cpu"


def test_healthy_corpus_yields_no_proposal() -> None:
    assert propose_specialists(_recs("MATH", 10, 1)) == []


def test_empty_corpus_yields_no_proposal() -> None:
    assert propose_specialists([]) == []


def test_proposing_never_registers_in_the_fleet() -> None:
    # THE human-gated guarantee: proposing must NOT mutate the FleetRegistry.
    before = set(get_registry().models.keys())
    propose_specialists(_recs("EXTRACTION", 10, 9))
    after = set(get_registry().models.keys())
    assert before == after  # no auto-registration
