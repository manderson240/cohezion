"""Item 640: cosmic_fire_cascade_actions() -- CosmicFireProtocol cascade at HIHO.

Thin wrapper: CosmicFireProtocol(notify_telegram=False).ignition_cascade(coherence).
Returns 5 ordered action strings when coherence >= 0.45 (HIHO band), else [].
Empty list for coherence outside [0,1].  Pure; no Telegram I/O.

Discriminating tests:
  1. PRIMARY DISC.: coherence=0.5 returns exactly 5 strings; cascade[0]='enter_bbq_low_slow_mode'.
     Wrong cascade order or missing entry kills impl.
  2. coherence < threshold (0.3) -> [].
  3. coherence=1.0 -> returns 5 strings (upper bound still in-band).
  4. coherence < 0.0 -> [].
  5. coherence > 1.0 -> [].
"""

from __future__ import annotations

from cohezion.compound.problem_discovery import (
    cosmic_fire_cascade_actions,
)


def test_hiho_coherence_returns_five_ordered_actions_primary_discriminator() -> None:
    """PRIMARY DISC.: coherence=0.5 -> 5 ordered strings, [0]='enter_bbq_low_slow_mode'.

    Kills impl returning wrong length, wrong order, or missing first action.
    """
    result = cosmic_fire_cascade_actions(0.5)
    assert isinstance(result, list), "Must return list; got " + repr(type(result))
    assert len(result) == 5, f"Must return 5 actions; got {len(result)}: {result}"
    assert result[0] == "enter_bbq_low_slow_mode", (
        f"First action must be 'enter_bbq_low_slow_mode'; got {result[0]!r}"
    )
    assert all(isinstance(a, str) for a in result), "All actions must be str"


def test_below_threshold_returns_empty() -> None:
    """coherence=0.3 (below 0.45 threshold) -> []."""
    result = cosmic_fire_cascade_actions(0.3)
    assert result == [], f"Below threshold (0.3) -> []; got {result}"


def test_max_coherence_returns_five_actions() -> None:
    """coherence=1.0 -> 5 actions (still in-band)."""
    result = cosmic_fire_cascade_actions(1.0)
    assert len(result) == 5, f"coherence=1.0 -> 5 actions; got {result}"


def test_negative_coherence_returns_empty() -> None:
    """coherence < 0.0 -> []."""
    result = cosmic_fire_cascade_actions(-0.1)
    assert result == [], f"Negative coherence -> []; got {result}"


def test_above_one_coherence_returns_empty() -> None:
    """coherence > 1.0 -> []."""
    result = cosmic_fire_cascade_actions(1.1)
    assert result == [], f"coherence > 1.0 -> []; got {result}"
