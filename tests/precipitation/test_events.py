"""Tests for PrecipitationEvent type and helpers."""

from __future__ import annotations

import pytest

from cohezion.precipitation.events import (
    FABRIC_DIMS,
    HIHO_BASELINE,
    TWELVE_D_DIMS,
    PrecipitationEvent,
    PrecipitationKind,
    compute_fabric_breakdown,
    zero_twelve_d,
)


def test_zero_twelve_d_has_all_dims_at_hiho_baseline() -> None:
    point = zero_twelve_d()
    assert set(point.keys()) == set(TWELVE_D_DIMS)
    for value in point.values():
        assert value == HIHO_BASELINE


def test_fabric_dims_partition_the_12d_space() -> None:
    covered: set[str] = set()
    for fabric, dims in FABRIC_DIMS.items():
        assert len(dims) == 3, f"fabric {fabric} should have 3 dims"
        covered.update(dims)
    assert covered == set(TWELVE_D_DIMS)


def test_compute_fabric_breakdown_averages_three_dims() -> None:
    point = dict.fromkeys(TWELVE_D_DIMS, 0.0)
    for dim in FABRIC_DIMS["Space"]:
        point[dim] = 0.9
    breakdown = compute_fabric_breakdown(point)
    assert breakdown["Space"] == pytest.approx(0.9)
    assert breakdown["Field"] == pytest.approx(0.0)


def test_precipitation_event_defaults_fabric_breakdown_from_twelve_d() -> None:
    twelve = zero_twelve_d()
    event = PrecipitationEvent(
        kind=PrecipitationKind.WITNESS_MARK,
        universe_id="u1",
        coherence=0.5,
        twelve_d=twelve,
    )
    for fabric in FABRIC_DIMS:
        assert event.fabric_breakdown[fabric] == pytest.approx(HIHO_BASELINE)


def test_precipitation_event_rejects_out_of_range_coherence() -> None:
    with pytest.raises(ValueError):
        PrecipitationEvent(
            kind=PrecipitationKind.WITNESS_MARK,
            universe_id="u1",
            coherence=1.5,
        )


def test_precipitation_event_fills_missing_dims_with_hiho_baseline() -> None:
    event = PrecipitationEvent(
        kind=PrecipitationKind.WITNESS_MARK,
        universe_id="u1",
        coherence=0.5,
        twelve_d={"x": 0.1},  # only 1 of 12 dims
    )
    assert len(event.twelve_d) == 12
    assert event.twelve_d["x"] == 0.1
    assert event.twelve_d["y"] == HIHO_BASELINE


def test_hiho_delta_and_is_coherent() -> None:
    hot = PrecipitationEvent(kind=PrecipitationKind.WITNESS_MARK, universe_id="u", coherence=0.7)
    cold = PrecipitationEvent(kind=PrecipitationKind.WITNESS_MARK, universe_id="u", coherence=0.3)
    assert hot.hiho_delta == pytest.approx(0.2)
    assert cold.hiho_delta == pytest.approx(-0.2)
    assert hot.is_coherent
    assert not cold.is_coherent


def test_to_dict_and_from_dict_round_trip() -> None:
    original = PrecipitationEvent(
        kind=PrecipitationKind.CONSENSUS_RATIFIED,
        universe_id="u42",
        coherence=0.88,
        agent_id="evo-007",
        payload={"directive": "ship it"},
        lineage=["parent-1", "parent-2"],
    )
    round_tripped = PrecipitationEvent.from_dict(original.to_dict())
    assert round_tripped.event_id == original.event_id
    assert round_tripped.kind == original.kind
    assert round_tripped.universe_id == original.universe_id
    assert round_tripped.coherence == pytest.approx(original.coherence)
    assert round_tripped.agent_id == original.agent_id
    assert round_tripped.payload == original.payload
    assert round_tripped.lineage == original.lineage
    assert round_tripped.twelve_d == original.twelve_d


def test_serialized_dict_uses_schema_compatible_keys() -> None:
    event = PrecipitationEvent(
        kind=PrecipitationKind.COSMOGONY_PHASE,
        universe_id="u",
        coherence=0.5,
    )
    data = event.to_dict()
    # Surreal schema has these as top-level columns:
    for key in [
        "event_id",
        "kind",
        "universe_id",
        "coherence",
        "hiho_delta",
        "twelve_d",
        "fabric_breakdown",
        "spinor_state",
        "payload",
        "valid_from",
        "transaction_time",
        "lineage",
    ]:
        assert key in data, f"missing top-level key {key}"
    # 12D dims must all be present under twelve_d
    for dim in TWELVE_D_DIMS:
        assert dim in data["twelve_d"]
