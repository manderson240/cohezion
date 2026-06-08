"""Item 168: snapshot_pipeline() — end-to-end TournamentSnapshot round-trip (2026-06-08).

``snapshot_pipeline(neurons, *, second_neurons=None)`` →
``tuple[TournamentSnapshot, TournamentSnapshot, TournamentSnapshotDiff, str]``:
exercises the full deposit→recall→diff→summary pipeline in a single call.

  - ``before = TournamentSnapshot.from_neurons(neurons)``
  - ``after  = TournamentSnapshot.from_neurons(second_neurons or neurons)``
  - ``diff   = tournament_snapshot_diff(before, after)``
  - ``report = diff_summary(diff)``

When ``second_neurons is None``, ``before == after`` (same neuron list), so the
diff has no added/removed/changed and the report is ``"No changes."``.

Pure; no I/O, no SurrealDB.

Discriminating tests — each kills a plausible wrong implementation:

  1. PRIMARY DISC.: self-diff (``second_neurons=None``) → ``report == "No changes."``
     AND ``diff.added == {}``.
     Kills an impl that forces a synthetic diff even for identical inputs.
  2. Cross-diff (different neuron lists) → ``diff.added`` is populated and
     ``report`` contains the new task name and model_id.
     Kills an impl that always returns the before snapshot as after.
  3. Return value is a 4-tuple in the exact order
     ``(before, after, diff, report)``.
     Kills an impl that reorders elements or returns a dict/dataclass.
  4. ``before`` and ``after`` are :class:`TournamentSnapshot` instances.
     Kills an impl that returns raw winner dicts instead of typed snapshots.
  5. ``diff`` is a :class:`TournamentSnapshotDiff` instance.
     Kills an impl that returns the diff as a plain dict.
"""

from __future__ import annotations

from cohezion.inference.registry import Task
from cohezion.inference.tournament_deposit import (
    TournamentSnapshot,
    TournamentSnapshotDiff,
    snapshot_pipeline,
)


# ---------------------------------------------------------------------------
# Helpers — injectable neuron store entries
# ---------------------------------------------------------------------------


def _winner_neuron(task: Task, model_id: str) -> dict:
    """Build a minimal tournament-winner neuron dict."""
    return {
        "name": f"{task.value}:tournament-winner",
        "content": model_id,
        "country": "inference",
        "tags": [task.value, "tournament-winner"],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_self_diff_produces_no_changes() -> None:
    """second_neurons=None (same neurons) → report == 'No changes.' AND diff.added=={}.

    PRIMARY DISCRIMINATOR: kills an impl that forces a diff even for equal inputs
    (e.g., one that always populates diff.added with all task values).
    """
    neurons = [_winner_neuron(Task.CODE_GEN, "model-alpha")]

    _before, _after, diff, report = snapshot_pipeline(neurons)

    assert report == "No changes.", f"Self-diff must produce 'No changes.'; got {report!r}"
    assert diff.added == {}, f"Self-diff must have empty added partition; got {diff.added!r}"
    assert diff.removed == set(), (
        f"Self-diff must have empty removed partition; got {diff.removed!r}"
    )
    assert diff.changed == {}, f"Self-diff must have empty changed partition; got {diff.changed!r}"


def test_cross_diff_shows_added_winner() -> None:
    """Different neuron lists → diff.added populated, report contains task and model.

    Kills an impl that always returns the before snapshot as after (never diffing).
    """
    before_neurons: list[dict] = []  # no winners yet
    after_neurons = [_winner_neuron(Task.CODE_GEN, "qwen3-coder")]

    _before, _after, diff, report = snapshot_pipeline(
        before_neurons,
        second_neurons=after_neurons,
    )

    assert Task.CODE_GEN.value in diff.added, f"CODE_GEN must be in diff.added; got {diff.added!r}"
    assert diff.added[Task.CODE_GEN.value] == "qwen3-coder", (
        f"Added model_id must be 'qwen3-coder'; got {diff.added.get(Task.CODE_GEN.value)!r}"
    )
    assert Task.CODE_GEN.value in report, f"report must contain the added task name; got {report!r}"
    assert "qwen3-coder" in report, f"report must contain the new model_id; got {report!r}"


def test_return_is_four_tuple() -> None:
    """Return value is a 4-tuple: (before, after, diff, report).

    Kills an impl that returns a dict, a 3-tuple, or a named dataclass
    with a different field order.
    """
    result = snapshot_pipeline([])

    assert isinstance(result, tuple), f"Expected tuple; got {type(result)}"
    assert len(result) == 4, f"Expected 4-tuple; got len={len(result)}"


def test_before_and_after_are_tournament_snapshots() -> None:
    """before and after are TournamentSnapshot instances.

    Kills an impl that returns raw winner dicts or plain frozensets.
    """
    neurons = [_winner_neuron(Task.SUMMARIZATION, "phi3-mini")]
    before, after, _diff, _report = snapshot_pipeline(neurons)

    assert isinstance(before, TournamentSnapshot), (
        f"before must be TournamentSnapshot; got {type(before)}"
    )
    assert isinstance(after, TournamentSnapshot), (
        f"after must be TournamentSnapshot; got {type(after)}"
    )


def test_diff_is_tournament_snapshot_diff() -> None:
    """diff is a TournamentSnapshotDiff instance.

    Kills an impl that returns the diff as a plain dict or None.
    """
    _, _, diff, _ = snapshot_pipeline([])

    assert isinstance(diff, TournamentSnapshotDiff), (
        f"diff must be TournamentSnapshotDiff; got {type(diff)}"
    )
