"""Discriminating tests for firing_concentration (backlog item 82, 2026-06-08).

`firing_concentration(usage_events, registry_skills)` → `{top_skill_share, unused_share,
total_firings}`: the top-heaviness scalar behind item-60's long tail. Shares item-60's
`_counts_per_registered_skill` core (unregistered firings ignored; never-fired registered skills
count toward unused_share). Report-only, pure over injected events.

Each test fails a plausible wrong impl:
  - an impl that divides unused by FIRED-skill count, not registered count → test_unused_share_over_all_registered,
  - an impl that counts unregistered firings → test_unregistered_firings_excluded,
  - an impl that ZeroDivisions on no events / empty registry → test_zero_events / test_empty_registry,
  - an impl that picks a non-max skill for the top share → test_top_share_is_the_max.
"""

from __future__ import annotations

from cohezion.compound.skill_adoption import FiringConcentration, firing_concentration


def _events(*names: str) -> list[dict]:
    return [{"skill_name": n} for n in names]


def test_nine_of_ten_to_one_skill() -> None:
    # registry {A,B,C,D}; A fires 9, B fires 1 → top_skill_share 0.9, unused {C,D} → 0.5.
    out = firing_concentration(_events(*(["A"] * 9 + ["B"])), ["A", "B", "C", "D"])
    assert out.top_skill_share == 0.9
    assert out.unused_share == 0.5
    assert out.total_firings == 10


def test_unused_share_over_all_registered() -> None:
    # DISCRIMINATING: 2 of 4 registered skills never fire. unused_share must be 2/4 == 0.5, NOT
    # 2/2 (an impl dividing by the count of FIRED skills) and NOT 0.
    out = firing_concentration(_events("A", "A", "B"), ["A", "B", "C", "D"])
    assert out.unused_share == 0.5


def test_unregistered_firings_excluded() -> None:
    # DISCRIMINATING: registry {A}; A fires twice, unregistered X fires 5 times. total_firings is 2
    # (NOT 7), and top_skill_share is 2/2 == 1.0 (X excluded from both numerator and denominator).
    out = firing_concentration(_events("A", "A", "X", "X", "X", "X", "X"), ["A"])
    assert out.total_firings == 2
    assert out.top_skill_share == 1.0
    assert out.unused_share == 0.0


def test_zero_events() -> None:
    # DISCRIMINATING: no events → top_skill_share 0.0 (no ZeroDivision), unused_share 1.0, total 0.
    out = firing_concentration([], ["A", "B", "C"])
    assert out.top_skill_share == 0.0
    assert out.unused_share == 1.0
    assert out.total_firings == 0


def test_empty_registry() -> None:
    # DISCRIMINATING: empty registry → no ZeroDivision on unused_share; firings to unregistered
    # skills are ignored, so total_firings is 0 and all shares are 0.0.
    out = firing_concentration(_events("A", "B"), [])
    assert out.top_skill_share == 0.0
    assert out.unused_share == 0.0
    assert out.total_firings == 0


def test_top_share_is_the_max() -> None:
    # DISCRIMINATING: top_skill_share is the MAX skill's share, regardless of insertion order.
    out = firing_concentration(_events("B", "A", "A", "A", "B", "B", "B", "B"), ["A", "B"])
    # B fires 5, A fires 3, total 8 → top is B's 5/8.
    assert out.top_skill_share == 5 / 8
    assert out.total_firings == 8
    assert out.unused_share == 0.0


def test_returns_dataclass() -> None:
    out = firing_concentration(_events("A"), ["A", "B"])
    assert isinstance(out, FiringConcentration)
    assert out.total_firings == 1 and out.top_skill_share == 1.0 and out.unused_share == 0.5
