"""Item 98: model_usecase_coverage — the INVERSE of item-62 coverage_gaps (TDD red→green).

`model_usecase_coverage(served_models, registry)` audits whether every served fleet model
maps to ≥1 Task via its registry task_affinity, or whether some models occupy compute with
NO routing purpose. Report-only, pure (injected model list + registry; no live serving).

Each test fails a plausible wrong impl:
  - iterates registry instead of served_models → test_unserved_registered_absent
  - marks covered even with empty task_affinity → test_no_affinity_is_no_usecase
  - skips served models NOT in the registry → test_unregistered_served_is_no_usecase
  - flags task gaps (item 62's concern) → test_task_gap_not_reported
  - crashes on empty input → test_empty_inputs_all_empty
"""

from __future__ import annotations


from cohezion.inference.local_coverage import model_usecase_coverage
from cohezion.inference.registry import Lane, ModelEntry, Task, WeightQuant


# ---------------------------------------------------------------------------
# Helpers — minimal injectable ModelEntry stubs
# ---------------------------------------------------------------------------


def _entry(model_id: str, tasks: frozenset[Task] = frozenset()) -> ModelEntry:
    """Minimal ModelEntry with just model_id + task_affinity set."""
    return ModelEntry(
        model_id=model_id,
        lane=Lane.NPU,
        endpoint="http://localhost:13306",
        runtime_backend="flm",
        task_affinity=tasks,
        weight_quant=WeightQuant.INT4,
        context_window=8192,
    )


# ---------------------------------------------------------------------------
# Covered: served + has task_affinity ≥1
# ---------------------------------------------------------------------------


def test_covered_model_has_task_affinity() -> None:
    """A served model with ≥1 task_affinity Task → in covered, NOT in no_usecase."""
    entries = [_entry("model-a", frozenset({Task.SENSING}))]
    result = model_usecase_coverage(["model-a"], entries)
    assert "model-a" in result.covered
    assert "model-a" not in result.no_usecase


def test_covered_model_with_multiple_tasks() -> None:
    """A model mapped to many tasks is still just one covered entry (not duplicated)."""
    entries = [_entry("model-b", frozenset({Task.ROUTING, Task.SUMMARIZATION, Task.CODE_GEN}))]
    result = model_usecase_coverage(["model-b"], entries)
    assert "model-b" in result.covered
    assert len([m for m in result.covered if m == "model-b"]) == 1  # no duplicates


# ---------------------------------------------------------------------------
# No-usecase: served but empty task_affinity
# ---------------------------------------------------------------------------


def test_no_affinity_is_no_usecase() -> None:
    """A served model whose registry entry has EMPTY task_affinity → no_usecase.

    Kills an impl that checks 'model is in registry' rather than 'model has affinity'.
    """
    entries = [_entry("model-c", frozenset())]  # registered but no Tasks assigned
    result = model_usecase_coverage(["model-c"], entries)
    assert "model-c" in result.no_usecase
    assert "model-c" not in result.covered


# ---------------------------------------------------------------------------
# No-usecase: served but NOT in registry
# ---------------------------------------------------------------------------


def test_unregistered_served_is_no_usecase() -> None:
    """A served model_id NOT present in the registry → no_usecase (unknown = no purpose).

    Kills an impl that silently skips unregistered served models.
    """
    entries = [_entry("known-model", frozenset({Task.REASONING}))]
    result = model_usecase_coverage(["unknown-model"], entries)
    assert "unknown-model" in result.no_usecase
    assert "unknown-model" not in result.covered


# ---------------------------------------------------------------------------
# MAIN DISCRIMINATOR: unserved registered model absent from BOTH lists
# ---------------------------------------------------------------------------


def test_unserved_registered_absent() -> None:
    """A model IN the registry but NOT in served_models → absent from BOTH lists.

    This is the PRINCIPAL discriminator: an impl that iterates registry entries
    instead of served_models will surface this model.
    """
    entries = [
        _entry("served-model", frozenset({Task.SENSING})),
        _entry("unserved-model", frozenset({Task.ROUTING})),
    ]
    result = model_usecase_coverage(["served-model"], entries)
    # "unserved-model" is registered with tasks, but NOT served → in neither list
    assert "unserved-model" not in result.covered, (
        "unregistered-but-not-served model must NOT appear in covered"
    )
    assert "unserved-model" not in result.no_usecase, (
        "unregistered-but-not-served model must NOT appear in no_usecase"
    )
    # The served model IS reported
    assert "served-model" in result.covered


def test_task_gap_not_reported() -> None:
    """A Task with no served model is NOT this report's concern (that's item 62's job).

    Report only says which SERVED models have no routing slot — not which Tasks
    have no served model.
    """
    entries = [_entry("the-only-model", frozenset({Task.SENSING}))]
    result = model_usecase_coverage(["the-only-model"], entries)
    # Task.ROUTING has no model at all — but this function doesn't report task gaps
    assert Task.ROUTING.value not in result.covered
    assert Task.ROUTING.value not in result.no_usecase


# ---------------------------------------------------------------------------
# Empty inputs
# ---------------------------------------------------------------------------


def test_empty_served_models_all_empty() -> None:
    """Empty served_models → both covered and no_usecase are empty (no crash)."""
    entries = [_entry("some-model", frozenset({Task.SENSING}))]
    result = model_usecase_coverage([], entries)
    assert len(result.covered) == 0
    assert len(result.no_usecase) == 0


def test_empty_registry_all_no_usecase() -> None:
    """Served models with an empty registry → all are no_usecase (unknown to the registry)."""
    result = model_usecase_coverage(["model-x", "model-y"], [])
    assert "model-x" in result.no_usecase
    assert "model-y" in result.no_usecase
    assert len(result.covered) == 0


def test_empty_both_empty() -> None:
    """Both empty inputs → both empty sets (no crash)."""
    result = model_usecase_coverage([], [])
    assert len(result.covered) == 0
    assert len(result.no_usecase) == 0


# ---------------------------------------------------------------------------
# Mixed: some covered, some no_usecase
# ---------------------------------------------------------------------------


def test_mixed_partition() -> None:
    """Some served models are covered, some are no_usecase — correctly split.

    Kills both 'always covered' and 'always no_usecase' impls.
    """
    entries = [
        _entry("model-with-task", frozenset({Task.CODE_GEN})),
        _entry("model-without-task", frozenset()),
    ]
    result = model_usecase_coverage(
        ["model-with-task", "model-without-task", "unregistered-model"],
        entries,
    )
    assert "model-with-task" in result.covered
    assert "model-without-task" in result.no_usecase
    assert "unregistered-model" in result.no_usecase
    # covered and no_usecase are disjoint
    assert result.covered.isdisjoint(result.no_usecase), (
        "covered and no_usecase must be disjoint — a model cannot be in both"
    )
