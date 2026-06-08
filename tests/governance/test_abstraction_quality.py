"""Discriminating tests for abstraction_quality (backlog item 92, 2026-06-08).

`abstraction_quality(neurons, *, min_volatile=1)` is the 4th deposit-quality dimension (grounded in
arXiv 2606.04703 ExpInternalization): flag neuron deposits whose `content` is INSTANCE-SPECIFIC —
carrying STRONG volatile tokens (file paths, hex ids/SHAs, UUIDs, ISO dates, times, line-refs)
rather than abstract principle-level. Report-only, pure over an injected neuron list.

Each test fails a plausible wrong impl:
  - an impl that flags any digit → test_incidental_bare_number_not_flagged,
  - an impl that misses a concrete path/SHA/line-ref → test_path/sha/linenumber flagged,
  - an impl that flags an abstract principle → test_abstract_principle_not_flagged,
  - an impl that crashes on a non-dict / missing content → test_robust_to_missing_content.
"""

from __future__ import annotations

from cohezion.governance.neuron_quality import abstraction_quality


def _n(name: str, content: str) -> dict:
    return {"name": name, "content": content, "country": "cerebellum", "tags": ["t"]}


def test_path_flagged() -> None:
    out = abstraction_quality([_n("p", "edit src/cohezion/executor.py to fix the wiring")])
    assert out == ["p"]


def test_sha_flagged() -> None:
    out = abstraction_quality([_n("s", "the regression landed in commit 89afebf7c last night")])
    assert out == ["s"]


def test_line_number_flagged() -> None:
    out = abstraction_quality([_n("l", "the lock releases at handler:42 before the write")])
    assert out == ["l"]


def test_iso_date_flagged() -> None:
    out = abstraction_quality([_n("d", "the OOM happened on 2026-06-07 during the SD-Turbo load")])
    assert out == ["d"]


def test_uuid_flagged() -> None:
    out = abstraction_quality([_n("u", "session 1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed crashed")])
    assert out == ["u"]


def test_abstract_principle_not_flagged() -> None:
    # A principle-level deposit with NO volatile tokens → not flagged (the ExpInternalization ideal).
    out = abstraction_quality(
        [_n("a", "always validate inputs at the boundary before processing them")]
    )
    assert out == []


def test_incidental_bare_number_not_flagged() -> None:
    # DISCRIMINATING: a bare incidental number is NOT a strong token. An impl that flags any digit
    # would wrongly flag this principle.
    out = abstraction_quality(
        [_n("b", "retry up to 3 times on a transient failure, then escalate")]
    )
    assert out == []


def test_fraction_not_flagged_as_path() -> None:
    # DISCRIMINATING: "3/4" is a fraction, NOT a file path (the path regex requires a letter).
    out = abstraction_quality([_n("f", "keep coherence near 3/4 of the band for stability")])
    assert out == []


def test_min_volatile_threshold() -> None:
    # With min_volatile=2, a single volatile token is below threshold → not flagged; two → flagged.
    one = [_n("one", "see executor.py:10 for the pattern")]  # path+line-ref = 2 tokens actually
    assert abstraction_quality([_n("single", "happened on 2026-06-07")], min_volatile=2) == []
    assert abstraction_quality(one, min_volatile=2) == ["one"]  # path + :10 → 2 strong tokens


def test_robust_to_missing_content_and_non_dict() -> None:
    neurons = [
        {"name": "no_content", "country": "cerebellum"},  # no content field
        "not a dict",  # non-dict entry
        _n("has_path", "in src/foo.py"),
    ]
    assert abstraction_quality(neurons) == ["has_path"]


def test_empty_store_empty() -> None:
    assert abstraction_quality([]) == []
