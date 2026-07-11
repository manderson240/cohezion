"""Multi-step trajectory persistence (ADDITIVE, 2026-07-11).

persist_cycle historically hardcoded total_steps=1 + a single-point
coherence_trajectory, so the vacuum-relaxation + Markov-trajectory experiments
(gated on total_steps > 1) could never ungate. The optional `trajectory` param
writes the full arrays; passing nothing preserves the exact prior behavior.

These tests inject the module's `_sql` function — they NEVER hit live SurrealDB.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

from cohezion.compound import compound_persist


@dataclass
class _FakePoint:
    coherence: float = 0.5
    efficiency: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class _FakeResult:
    success: bool = True
    metrics: dict[str, Any] = field(default_factory=lambda: {"quality_score": 0.9})
    duration_seconds: float = 1.0


def _run(trajectory):
    """Call persist_cycle with _sql mocked; return the transaction query string."""
    captured: dict[str, str] = {}

    def fake_sql(query: str, *, timeout: float = 10.0):
        # First call is the multi-statement transaction; later calls are the
        # per-table SELECT count() — return a shape that survives BOTH the ERR
        # check (status != "ERR") and the count loop (res[-1]["result"][0]["count"]).
        if "BEGIN TRANSACTION" in query:
            captured["query"] = query
        return [{"status": "OK", "result": [{"count": 1}]}]

    with patch.object(compound_persist, "_sql", side_effect=fake_sql):
        compound_persist.persist_cycle(
            _FakePoint(),
            _FakeResult(),
            task_description="multistep test",
            skill_name="multistep-skill",
            learning="quality=0.9 tier=npu op=generate",
            run_id="cycle-multistep-1",
            trajectory=trajectory,
        )
    return captured["query"]


def test_trajectory_writes_full_arrays_and_total_steps():
    traj = [
        _FakePoint(coherence=0.2, efficiency=0.3),
        _FakePoint(coherence=0.5, efficiency=0.6),
        _FakePoint(coherence=0.8, efficiency=0.9, metadata={"phi_score": 0.77}),
    ]
    query = _run(traj)

    assert "total_steps: 3" in query
    assert "coherence_trajectory: [0.2, 0.5, 0.8]" in query
    assert "efficiency_trajectory: [0.3, 0.6, 0.9]" in query
    # final_* come from the LAST point (coherence 0.8, phi from metadata 0.77)
    assert "final_coherence: 0.8" in query
    assert "final_phi_score: 0.77" in query


def test_none_trajectory_preserves_single_step_backward_compat():
    query = _run(None)

    assert "total_steps: 1" in query
    assert "coherence_trajectory: [0.5]" in query
    assert "efficiency_trajectory: [0.5]" in query


def test_empty_trajectory_behaves_like_none():
    # `if trajectory:` (truthy) — an empty list must fall through to the
    # single-point path, never total_steps: 0 or a trajectory[-1] IndexError.
    query = _run([])

    assert "total_steps: 1" in query
    assert "coherence_trajectory: [0.5]" in query
