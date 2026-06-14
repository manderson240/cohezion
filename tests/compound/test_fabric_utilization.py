"""Item 114: fabric_utilization + place_task heterogeneous-fabric report (TDD red→green).

Reports per-engine (NPU/iGPU/CPU) utilization and proposes task placement.
Pure (injected Engine list; no live :13305/:13306/:13307 under pytest).

Discriminating tests — each kills a plausible wrong implementation:
  - CPU with 0 loaded models → flagged IDLE        (PRIMARY DISC. for utilization)
  - task=interactive → iGPU proposed               (PRIMARY DISC. for placement)
  - preferred engine at capacity → spillover        (kills ignore-capacity impl)
  - task=batch → NPU; deep_reasoning → CPU         (kills flat-routing impl)
  - all engines at capacity → None                 (kills always-place impl)
  - empty engines → empty report                   (baseline)
"""

from __future__ import annotations

from cohezion.compound.fabric_utilization import Engine, fabric_utilization, place_task


# ---------------------------------------------------------------------------
# Utilization report tests
# ---------------------------------------------------------------------------


def test_cpu_idle_when_no_models_loaded() -> None:
    """CPU with 0 loaded models → is_idle=True.

    PRIMARY DISCRIMINATOR for utilization: kills an impl that always sets is_idle=False.
    Mirrors the live finding (CPU=0 LLMs at 2026-06-06).
    """
    engines = [
        Engine(kind="npu", loaded_models=("llama3.2-1b-FLM",), capacity=4, in_flight=1),
        Engine(kind="igpu", loaded_models=("Qwen3.6-A3B", "nomic-embed"), capacity=3, in_flight=2),
        Engine(kind="cpu", loaded_models=(), capacity=8, in_flight=0),
    ]
    report = fabric_utilization(engines)
    assert report["cpu"].is_idle is True, "CPU with no models must be flagged IDLE"


def test_npu_not_idle_when_model_loaded() -> None:
    """NPU with a model loaded → is_idle=False."""
    engines = [Engine(kind="npu", loaded_models=("llama3.2-1b-FLM",), capacity=4, in_flight=0)]
    report = fabric_utilization(engines)
    assert report["npu"].is_idle is False


def test_at_capacity_flagged() -> None:
    """An engine where in_flight >= capacity → at_capacity=True."""
    engines = [Engine(kind="npu", loaded_models=("llama",), capacity=4, in_flight=4)]
    report = fabric_utilization(engines)
    assert report["npu"].at_capacity is True


def test_loaded_models_forwarded() -> None:
    """The report forwards the loaded model list verbatim."""
    models = ("llama3.2-1b-FLM", "nomic-embed-text-v2")
    engines = [Engine(kind="npu", loaded_models=models, capacity=4, in_flight=0)]
    report = fabric_utilization(engines)
    assert report["npu"].loaded_models == list(models)


def test_empty_engines_empty_report() -> None:
    """No engines → empty report. No crash."""
    assert fabric_utilization([]) == {}


# ---------------------------------------------------------------------------
# Placement tests
# ---------------------------------------------------------------------------


def test_interactive_placed_on_igpu() -> None:
    """task_kind=interactive → proposed engine is iGPU.

    PRIMARY DISCRIMINATOR for placement: kills an impl that ignores task type.
    """
    engines = [
        Engine(kind="npu", loaded_models=("llama",), capacity=4, in_flight=0),
        Engine(kind="igpu", loaded_models=("qwen",), capacity=3, in_flight=0),
        Engine(kind="cpu", loaded_models=("gemma",), capacity=8, in_flight=0),
    ]
    assert place_task("interactive", engines=engines) == "igpu"


def test_batch_placed_on_npu() -> None:
    """task_kind=batch → proposed engine is NPU (fast, cheap)."""
    engines = [
        Engine(kind="npu", loaded_models=("llama",), capacity=4, in_flight=0),
        Engine(kind="igpu", loaded_models=("qwen",), capacity=3, in_flight=0),
    ]
    assert place_task("batch", engines=engines) == "npu"


def test_classify_placed_on_npu() -> None:
    """task_kind=classify → proposed engine is NPU (mirrors batch routing)."""
    engines = [
        Engine(kind="npu", loaded_models=("llama",), capacity=4, in_flight=0),
        Engine(kind="igpu", loaded_models=("qwen",), capacity=3, in_flight=0),
    ]
    assert place_task("classify", engines=engines) == "npu"


def test_deep_reasoning_placed_on_cpu() -> None:
    """task_kind=deep_reasoning → proposed engine is CPU (large context, slow)."""
    engines = [
        Engine(kind="npu", loaded_models=("llama",), capacity=4, in_flight=0),
        Engine(kind="igpu", loaded_models=("qwen",), capacity=3, in_flight=0),
        Engine(kind="cpu", loaded_models=("gemma31b",), capacity=8, in_flight=0),
    ]
    assert place_task("deep_reasoning", engines=engines) == "cpu"


def test_at_capacity_engine_causes_spillover() -> None:
    """NPU at capacity → batch task spills over to next available engine.

    Kills an impl that ignores in_flight/capacity state.
    """
    engines = [
        Engine(kind="npu", loaded_models=("llama",), capacity=4, in_flight=4),  # FULL
        Engine(kind="igpu", loaded_models=("qwen",), capacity=3, in_flight=0),
        Engine(kind="cpu", loaded_models=("gemma",), capacity=8, in_flight=0),
    ]
    proposal = place_task("batch", engines=engines)
    assert proposal != "npu", "NPU is full; batch must spill to another engine"
    assert proposal is not None, "Some available engine must be proposed"


def test_all_engines_at_capacity_returns_none() -> None:
    """All engines at capacity → None (cannot place task; report-only).

    Kills an impl that always returns an engine name.
    """
    engines = [
        Engine(kind="npu", loaded_models=("llama",), capacity=1, in_flight=1),
        Engine(kind="igpu", loaded_models=("qwen",), capacity=1, in_flight=1),
        Engine(kind="cpu", loaded_models=("gemma",), capacity=1, in_flight=1),
    ]
    assert place_task("batch", engines=engines) is None
