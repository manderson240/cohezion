"""Item 114: fabric_utilization + place_task — TDD red→green.

`fabric_utilization(loaded_models, engines)` reports per-engine utilization.
`place_task(task, *, engines)` proposes which engine to run a task on.

Discriminating tests — each kills a plausible wrong implementation:
  - cpu with 0 models → IDLE                               → test_cpu_idle_when_empty (MAIN DISC.)
  - engine with models → NOT idle                          → test_loaded_engine_not_idle
  - place_task interactive → igpu                          → test_place_interactive_on_igpu
  - place_task batch/classify → npu                        → test_place_batch_on_npu
  - place_task deep-reasoning → cpu                        → test_place_reasoning_on_cpu
  - engine at capacity → task NOT placed there (spillover) → test_at_capacity_spillover
  - empty engines → all idle                               → test_empty_engines_all_idle
  - all engines at capacity → None (no placement)         → test_all_full_returns_none
"""

from __future__ import annotations

from cohezion.inference.fabric import EngineSpec, fabric_utilization, place_task

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec(name: str, models: list[str] = None, capacity: int = 4) -> EngineSpec:
    return EngineSpec(name=name, loaded_models=models or [], capacity=capacity)


# ---------------------------------------------------------------------------
# fabric_utilization
# ---------------------------------------------------------------------------


def test_cpu_idle_when_empty() -> None:
    """CPU with 0 loaded models → is_idle=True.

    PRIMARY DISCRIMINATOR: models the live finding (CPU=0 LLMs, 2026-06-06).
    Kills an impl that always sets is_idle=False.
    """
    engines = [_spec("cpu", models=[])]
    report = fabric_utilization(engines)
    assert "cpu" in report
    assert report["cpu"].is_idle is True, f"cpu with 0 models must be idle; got {report['cpu']}"


def test_loaded_engine_not_idle() -> None:
    """iGPU with models loaded → is_idle=False.

    Kills an impl that marks all engines idle.
    """
    engines = [_spec("igpu", models=["gemma-4b", "granite-3b", "deepseek-r1"])]
    report = fabric_utilization(engines)
    assert report["igpu"].is_idle is False


def test_npu_reports_model_count() -> None:
    """NPU with 1 model → loaded_count=1."""
    engines = [_spec("npu", models=["llama3.2-1b-FLM"])]
    report = fabric_utilization(engines)
    assert report["npu"].loaded_count == 1


def test_empty_engines_all_idle() -> None:
    """No engines passed → empty report."""
    report = fabric_utilization([])
    assert report == {}


def test_mixed_fabric() -> None:
    """NPU+iGPU loaded, CPU empty → cpu is idle, others are not."""
    engines = [
        _spec("npu", models=["llama3.2-1b-FLM"]),
        _spec("igpu", models=["gemma-4b", "granite-3b", "deepseek-r1"]),
        _spec("cpu", models=[]),
    ]
    report = fabric_utilization(engines)
    assert report["cpu"].is_idle is True
    assert report["npu"].is_idle is False
    assert report["igpu"].is_idle is False


def test_at_capacity_flagged() -> None:
    """Engine with loaded_count == capacity → at_capacity=True."""
    engines = [_spec("igpu", models=["a", "b", "c", "d"], capacity=4)]
    report = fabric_utilization(engines)
    assert report["igpu"].at_capacity is True


def test_under_capacity_not_flagged() -> None:
    """Engine with loaded_count < capacity → at_capacity=False."""
    engines = [_spec("igpu", models=["a", "b"], capacity=4)]
    report = fabric_utilization(engines)
    assert report["igpu"].at_capacity is False


# ---------------------------------------------------------------------------
# place_task
# ---------------------------------------------------------------------------


def test_place_interactive_on_igpu() -> None:
    """Task 'interactive' → placed on igpu.

    Kills an impl that always uses NPU or uses alphabetical order.
    """
    engines = [
        _spec("npu", capacity=4),
        _spec("igpu", capacity=4),
        _spec("cpu", capacity=4),
    ]
    placement = place_task("interactive", engines=engines)
    assert placement == "igpu", f"interactive task must go to igpu; got {placement}"


def test_place_batch_on_npu() -> None:
    """Task 'batch' → placed on npu."""
    engines = [_spec("npu"), _spec("igpu"), _spec("cpu")]
    placement = place_task("batch", engines=engines)
    assert placement == "npu", f"batch task must go to npu; got {placement}"


def test_place_classify_on_npu() -> None:
    """Task 'classify' → placed on npu (same as batch — classification workload)."""
    engines = [_spec("npu"), _spec("igpu"), _spec("cpu")]
    placement = place_task("classify", engines=engines)
    assert placement == "npu"


def test_place_reasoning_on_cpu() -> None:
    """Task 'deep-reasoning' → placed on cpu."""
    engines = [_spec("npu"), _spec("igpu"), _spec("cpu")]
    placement = place_task("deep-reasoning", engines=engines)
    assert placement == "cpu", f"deep-reasoning task must go to cpu; got {placement}"


def test_at_capacity_spillover() -> None:
    """Preferred engine at capacity → task placed on next engine (spillover).

    Kills an impl that places on a full engine or returns None prematurely.
    """
    # interactive → igpu, but igpu is full → spill to cpu
    engines = [
        _spec("npu", capacity=4),
        _spec("igpu", models=["a", "b", "c", "d"], capacity=4),  # at capacity
        _spec("cpu", capacity=4),
    ]
    placement = place_task("interactive", engines=engines)
    assert placement in ("npu", "cpu"), (
        f"igpu full → interactive must spill to another engine; got {placement}"
    )
    assert placement != "igpu", f"igpu is at capacity; must not be chosen; got {placement}"


def test_all_full_returns_none() -> None:
    """All engines at capacity → place_task returns None (no placement possible)."""
    engines = [
        _spec("npu", models=["a", "b", "c", "d"], capacity=4),
        _spec("igpu", models=["a", "b", "c", "d"], capacity=4),
        _spec("cpu", models=["a", "b", "c", "d"], capacity=4),
    ]
    placement = place_task("interactive", engines=engines)
    assert placement is None, f"All engines full → None; got {placement}"
