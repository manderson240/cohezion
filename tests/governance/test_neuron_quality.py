"""Discriminating tests for the neuron-store deposit-quality audit (item 52, 2026-06-06).

`deposit_quality_report(neurons)` measures TaskMem's 3 memory-quality dimensions (arXiv 2605.31075 —
the taxonomy, NOT its RL-on-30B-VL method) over DEPOSITED neurons: non-redundancy / evidence / format.
Report-only; operates on an injected neuron list (never reads SurrealDB).

Each test fails a plausible wrong impl:
  - misses a duplicate name / miscounts → test_redundant_duplicate_names,
  - wrong evidence-floor comparison → test_low_evidence_below_floor,
  - doesn't flag a neuron missing a required field → test_format_invalid_missing_field,
  - flags a clean store → test_clean_store_all_empty.
"""

from __future__ import annotations

from cohezion.governance.neuron_quality import deposit_quality_report


def _neuron(name: str, *, country: str = "cerebellum", tags=("x",), reward: float = 1.0) -> dict:
    return {"name": name, "country": country, "tags": list(tags), "reward": reward, "content": "c"}


def test_redundant_duplicate_names() -> None:
    rep = deposit_quality_report([_neuron("foo"), _neuron("foo"), _neuron("bar")])
    assert rep.redundant == {"foo": 2}  # foo deposited twice; bar unique


def test_low_evidence_below_floor() -> None:
    rep = deposit_quality_report(
        [_neuron("a", reward=0.3), _neuron("b", reward=0.9)], evidence_floor=0.5
    )
    assert rep.low_evidence == ["a"]  # 0.3 < 0.5; 0.9 not


def test_evidence_floor_is_strict_boundary() -> None:
    # reward exactly == floor is NOT low-evidence (strictly below).
    rep = deposit_quality_report([_neuron("a", reward=0.5)], evidence_floor=0.5)
    assert rep.low_evidence == []


def test_format_invalid_missing_field() -> None:
    missing_country = {"name": "x", "tags": ["t"], "reward": 1.0}  # no country
    empty_tags = {
        "name": "y",
        "country": "skill",
        "tags": [],
        "reward": 1.0,
    }  # untagged → unrecallable
    rep = deposit_quality_report([missing_country, empty_tags, _neuron("ok")])
    assert set(rep.format_invalid) == {"x", "y"}
    assert "ok" not in rep.format_invalid


def test_clean_store_all_empty() -> None:
    rep = deposit_quality_report([_neuron("a"), _neuron("b"), _neuron("c")])
    assert rep.redundant == {} and rep.low_evidence == [] and rep.format_invalid == []


def test_malformed_entries_do_not_crash() -> None:
    rep = deposit_quality_report([_neuron("a"), "junk", {}, None])  # type: ignore[list-item]
    assert rep.redundant == {}  # 'a' unique; non-dicts ignored for redundancy
