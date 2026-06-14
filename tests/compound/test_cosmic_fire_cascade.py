"""Item 640: cosmic_fire_cascade_actions() -- CosmicFireProtocol cascade at HIHO.

Thin wrapper exposing CosmicFireProtocol.ignition_cascade() for TIDE-layer testing.
Returns ordered 5-action list at coherence >= 0.45 (P3 invariant coverage).
Empty list below threshold.  Pure; no I/O (notify_telegram=False).
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import cosmic_fire_cascade_actions


_EXPECTED_CASCADE = [
    "enter_bbq_low_slow_mode",
    "spawn_r0_adversarial_review",
    "escalate_to_cpu_cloud_tier",
    "persist_cosmic_fire_event",
    "telegram_notify_ignition",
]


def test_hiho_threshold_fires_exactly_five_actions_primary_discriminator() -> None:
    """PRIMARY DISC.: coherence=0.5 (HIHO) returns exactly 5 ordered actions.

    First action must be 'enter_bbq_low_slow_mode'.
    Kills impl returning wrong count, wrong order, or wrong first action.
    """
    result = cosmic_fire_cascade_actions(0.5)
    assert isinstance(result, list), f"Must return list; got {type(result)}"
    assert len(result) == 5, f"Must have exactly 5 actions; got {len(result)}: {result}"
    assert result[0] == "enter_bbq_low_slow_mode", (
        f"First action must be 'enter_bbq_low_slow_mode'; got '{result[0]}'"
    )
    assert result == _EXPECTED_CASCADE, f"Wrong cascade order or wrong actions; got {result}"


def test_below_threshold_returns_empty_list() -> None:
    """coherence < 0.45 (below threshold) -> empty list (no ignition)."""
    result = cosmic_fire_cascade_actions(0.3)
    assert result == [], f"Below threshold -> []; got {result}"


def test_at_exact_threshold_ignites() -> None:
    """coherence=0.45 (exact threshold) -> 5-action cascade fires."""
    result = cosmic_fire_cascade_actions(0.45)
    assert len(result) == 5, f"At threshold 0.45 -> 5 actions; got {len(result)}"
    assert result[0] == "enter_bbq_low_slow_mode"


def test_zero_coherence_no_ignition() -> None:
    """coherence=0.0 -> empty list."""
    assert cosmic_fire_cascade_actions(0.0) == []


def test_full_coherence_fires() -> None:
    """coherence=1.0 (max) -> full cascade fires."""
    result = cosmic_fire_cascade_actions(1.0)
    assert len(result) == 5, f"Max coherence -> 5 actions; got {len(result)}"
    assert result == _EXPECTED_CASCADE
