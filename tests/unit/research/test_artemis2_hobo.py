"""Offline tests for research/artemis2/analyze_hobo.py (no network, synthetic data).

Each test pins one piece of logic that a README claim depends on, and fails if that
logic is neutralised: the transient detector, the phase boundaries, the derived
humidity, the CDT->UTC conversion, the label parser and the checksum gate.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest


_PATH = Path(__file__).resolve().parents[3] / "research" / "artemis2" / "analyze_hobo.py"
_spec = importlib.util.spec_from_file_location("analyze_hobo", _PATH)
hobo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hobo)

LAUNCH = hobo.EVENTS["launch"]


def _flat_rh(minutes: int, start: datetime, rh: float = 25.0) -> pl.DataFrame:
    t = [start + timedelta(minutes=i) for i in range(minutes)]
    return hobo.with_derived(
        pl.DataFrame({"utc": t, "seq": range(1, minutes + 1), "T": 22.0, "RH": rh, "Td": 2.0})
    )


def _spike(df: pl.DataFrame, at: datetime, amount: float) -> pl.DataFrame:
    return df.with_columns(
        RH=pl.when(pl.col("utc") == at).then(pl.col("RH") + amount).otherwise(pl.col("RH"))
    )


class TestTransientEvents:
    def test_single_spike_is_found_with_its_excess(self):
        df = _flat_rh(600, LAUNCH)
        at = LAUNCH + timedelta(minutes=300)
        events = hobo.transient_events(_spike(df, at, 5.0), 1.5)
        assert events == [{"at": hobo.fmt(at), "rh_excess_pct": 5.0}]

    def test_flat_series_has_no_events(self):
        assert hobo.transient_events(_flat_rh(600, LAUNCH), 1.0) == []

    def test_threshold_is_respected(self):
        df = _spike(_flat_rh(600, LAUNCH), LAUNCH + timedelta(minutes=300), 1.2)
        assert hobo.transient_events(df, 1.5) == []
        assert len(hobo.transient_events(df, 1.0)) == 1

    def test_cluster_keeps_largest_peak_not_first(self):
        df = _flat_rh(600, LAUNCH)
        first, bigger = LAUNCH + timedelta(minutes=300), LAUNCH + timedelta(minutes=320)
        df = _spike(_spike(df, first, 2.0), bigger, 6.0)
        events = hobo.transient_events(df, 1.5)
        assert [e["at"] for e in events] == [hobo.fmt(bigger)]

    def test_spikes_more_than_30_min_apart_are_separate(self):
        df = _flat_rh(600, LAUNCH)
        a, b = LAUNCH + timedelta(minutes=200), LAUNCH + timedelta(minutes=260)
        assert len(hobo.transient_events(_spike(_spike(df, a, 3.0), b, 3.0), 1.5)) == 2

    def test_window_excludes_spikes_outside_it(self):
        df = _flat_rh(600, LAUNCH)
        at = LAUNCH + timedelta(minutes=300)
        out = hobo.transient_events(
            _spike(df, at, 5.0), 1.5, LAUNCH, LAUNCH + timedelta(minutes=100)
        )
        assert out == []


class TestPhases:
    def test_bins_are_right_closed(self):
        e = hobo.EVENTS
        t = [
            e["launch"],
            e["launch"] + timedelta(seconds=1),
            e["splashdown"],
            e["splashdown"] + timedelta(seconds=1),
        ]
        got = pl.DataFrame({"utc": t}).select(phase=hobo.phase_expr())["phase"].to_list()
        assert got == [hobo.PHASES[0], hobo.PHASES[1], hobo.PHASES[1], hobo.PHASES[2]]


class TestDerived:
    def test_absolute_humidity_saturated_air_at_20c(self):
        df = hobo.with_derived(pl.DataFrame({"T": [20.0], "RH": [100.0]}))
        assert df["AH"][0] == pytest.approx(17.3, abs=0.1)  # textbook value at 20 C

    def test_magnus_dewpoint_reference(self):
        out = pl.DataFrame({"T": [20.0], "RH": [50.0]}).select(
            hobo.magnus_dewpoint(pl.col("T"), pl.col("RH"))
        )
        assert out.to_series()[0] == pytest.approx(9.27, abs=0.05)


class TestLoading:
    def test_cdt_rows_become_utc_plus_five_hours(self, tmp_path):
        p = tmp_path / "x.csv"
        p.write_text(
            '#,Date-Time (CDT),"Temperature , deg C","RH , %","Dew Point , deg C"\n1,03/26/2026 11:25:46,21.13,28.253,2.05\n'
        )
        df = hobo.load(p)
        assert df["utc"][0] == datetime(2026, 3, 26, 16, 25, 46, tzinfo=UTC)
        assert "AH" in df.columns

    def test_label_stats_parsed_from_xml(self, tmp_path):
        p = tmp_path / "x.xml"
        p.write_text(
            "<Field_Delimited><name>Temperature</name><Field_Statistics><maximum>25.57</maximum>"
            "<minimum>17.77</minimum><mean>22.06</mean><standard_deviation>1.75</standard_deviation>"
            "</Field_Statistics></Field_Delimited>"
        )
        assert hobo.label_stats(p) == {"T": (25.57, 17.77, 22.06, 1.75)}

    def test_checksum_gate_rejects_a_tampered_file(self, tmp_path):
        name = next(iter(hobo.MD5))
        (tmp_path / name).write_text("not the PDS file\n")
        with pytest.raises(ValueError, match="MD5 mismatch"):
            hobo._get(tmp_path, name)
