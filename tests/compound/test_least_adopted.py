"""Ranked least-adopted skills queue (item 60, 2026-06-06) — claude.com #16's "investigate first" list.

`least_adopted(usage_events, registry_skills, *, n)` counts ALL registered skills (no threshold) and
returns the `n` lowest-firing as `[(skill, count)]` ASCENDING, ties broken by name — the prioritized
worst-under-triggers queue. Distinct from item-41 `low_adoption_report` (threshold-gated, unordered
map); shares the per-skill counting.

Each test fails a plausible wrong impl:
  - wrong sort direction / wrong N → test_bottom_n_ascending_name_tiebroken,
  - a never-fired registered skill omitted or not count 0 → test_never_fired_sorts_first_count_zero,
  - counts an unregistered firing → test_unregistered_firing_ignored,
  - n=0 not empty, or n>=len not all → test_n_bounds.
"""

from __future__ import annotations

from cohezion.compound.skill_adoption import least_adopted


def _ev(name: str) -> dict:
    return {"skill_name": name}


def test_bottom_n_ascending_name_tiebroken() -> None:
    registry = ["alpha", "bravo", "charlie", "delta"]
    events = [_ev("alpha")] * 5 + [_ev("bravo")] * 1 + [_ev("charlie")] * 1 + [_ev("delta")] * 9
    # bottom-3 by count ascending: bravo(1), charlie(1) tie→name order, alpha(5)
    assert least_adopted(events, registry, n=3) == [("bravo", 1), ("charlie", 1), ("alpha", 5)]


def test_never_fired_sorts_first_count_zero() -> None:
    registry = ["used", "never"]
    out = least_adopted([_ev("used")], registry, n=2)
    assert out[0] == ("never", 0)  # zero-count sorts ahead of the used skill
    assert ("used", 1) in out


def test_unregistered_firing_ignored() -> None:
    registry = ["reg"]
    # "ghost" fires but is not registered → must not appear; reg has count 0.
    assert least_adopted([_ev("ghost"), _ev("ghost")], registry, n=5) == [("reg", 0)]


def test_n_bounds() -> None:
    registry = ["a", "b", "c"]
    assert least_adopted([_ev("a")], registry, n=0) == []  # n=0 → empty
    full = least_adopted([_ev("a")], registry, n=99)  # n >= len → all, ranked
    assert [s for s, _ in full] == ["b", "c", "a"]  # b,c count 0 (name order), a count 1
