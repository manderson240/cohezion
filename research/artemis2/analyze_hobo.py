"""Artemis II Orion locker environment (HOBO MX1101) analysis.

Downloads the two HOBO logger tables from the PDS Geosciences Node Artemis II
Mission Bundle (released 2026-10-07) and characterises them against the
mission timeline in the Artemis II Lunar Science Data User Guide.

Usage:
    python research/artemis2/analyze_hobo.py [--data-dir DIR] [--out-dir DIR]

Requires: numpy, polars, matplotlib. Every number quoted in README.md section 1 is
written to hobo_results.json by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl


BASE = "https://pds-geosciences.wustl.edu/artemis2/urn-nasa-pds-artemis2_mission/data_orion_environment/"
FILES = {
    "SN1104": "art002_086-162546_111-205046_hobo1104_raw_v01",
    "SN1105": "art002_086-162926_111-203826_hobo1105_raw_v01",
}
# From the bundle manifest urn-nasa-pds-artemis2_mission.md5 (PDS release 2026-10-07).
MD5 = {
    "art002_086-162546_111-205046_hobo1104_raw_v01.csv": "ef6a42e7d2189ab2329121995d8446f1",
    "art002_086-162546_111-205046_hobo1104_raw_v01.xml": "8b32527433bed7cb659a7778f9893c12",
    "art002_086-162926_111-203826_hobo1105_raw_v01.csv": "f5ed3754e04d8a216955d5dea838986a",
    "art002_086-162926_111-203826_hobo1105_raw_v01.xml": "d5ef9dd100cf3a5320e321f6d482264d",
}
MAX_BYTES = 10_000_000


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


# Mission timeline (UTC), from the Data User Guide sections 2 and 3.4.
EVENTS = {
    k: _ts(v)
    for k, v in {
        "launch": "2026-04-01 22:35:12",
        "tli_day_start": "2026-04-02 18:15:12",
        "closest_approach": "2026-04-06 23:00:00",
        "eclipse_obs_end": "2026-04-07 01:45:00",
        "sn1105_move_window_start": "2026-04-09 18:00:00",
        "sn1105_move_window_end": "2026-04-09 21:00:00",
        "splashdown": "2026-04-11 00:07:00",
        "orion_power_down": "2026-04-11 00:30:00",
        "well_deck": "2026-04-11 08:14:00",
        "cargo_handover_after": "2026-04-14 19:00:00",
    }.items()
}
MIN = timedelta(minutes=1)
LABEL_FIELDS = {"Temperature": "T", "Relative Humidity": "RH", "Dew Point": "Td"}
PHASES = [
    "1 pre-launch (pad)",
    "2 flight",
    "3 ocean / recovery",
    "4 ship, pre-handover",
    "5 post-handover",
]


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes(), usedforsecurity=False).hexdigest()


def _get(data_dir: Path, name: str) -> Path:
    """Download one file (if absent) and verify it against the PDS manifest MD5."""
    p = data_dir / name
    if not p.exists():
        part = p.with_suffix(p.suffix + ".part")
        with urllib.request.urlopen(BASE + name, timeout=120) as r:  # noqa: S310 -- fixed https constant
            body = r.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError(f"{name}: larger than {MAX_BYTES} bytes")
        part.write_bytes(body)
        part.replace(p)
    if _md5(p) != MD5[name]:
        raise ValueError(f"{name}: MD5 mismatch with PDS manifest; delete it and re-run")
    return p


def fetch(data_dir: Path) -> dict[str, tuple[Path, Path]]:
    data_dir.mkdir(parents=True, exist_ok=True)
    return {sn: (_get(data_dir, f"{b}.csv"), _get(data_dir, f"{b}.xml")) for sn, b in FILES.items()}


def label_stats(xml_path: Path) -> dict[str, tuple[float, float, float, float]]:
    """(max, min, mean, std) per field from the PDS4 label's Field_Statistics blocks."""
    text = xml_path.read_text()
    out = {}
    for block in re.findall(r"<Field_Delimited>(.*?)</Field_Delimited>", text, re.S):
        name = re.search(r"<name>(.*?)</name>", block).group(1).strip()
        if name in LABEL_FIELDS and "<Field_Statistics>" in block:
            vals = [
                float(re.search(rf"<{k}>(.*?)</{k}>", block).group(1))
                for k in ("maximum", "minimum", "mean", "standard_deviation")
            ]
            out[LABEL_FIELDS[name]] = tuple(vals)
    return out


def with_derived(df: pl.DataFrame) -> pl.DataFrame:
    """Add absolute humidity (g/m^3), which separates added moisture from temperature-driven RH swings."""
    es = 6.112 * (17.67 * pl.col("T") / (pl.col("T") + 243.5)).exp()  # hPa
    return df.with_columns(AH=216.7 * (pl.col("RH") / 100 * es) / (273.15 + pl.col("T")))


def load(path: Path) -> pl.DataFrame:
    df = pl.read_csv(path, new_columns=["seq", "cdt", "T", "RH", "Td"])
    # Label: "Central Daylight Time (UTC-5)". DST runs 2026-03-08..11-01, so +5 h holds throughout.
    utc = (
        pl.col("cdt").str.to_datetime("%m/%d/%Y %H:%M:%S", time_unit="us") + pl.duration(hours=5)
    ).dt.replace_time_zone("UTC")
    return with_derived(df.with_columns(utc=utc).drop("cdt")).sort("utc")


def magnus_dewpoint(t: pl.Expr, rh: pl.Expr) -> pl.Expr:
    # Magnus-Tetens (Alduchov & Eskridge 1996 coefficients).
    a, b = 17.625, 243.04
    g = (rh / 100.0).log() + a * t / (b + t)
    return b * g / (a - g)


def phase_expr(col: str = "utc") -> pl.Expr:
    """Right-closed phase bins: (start, launch], (launch, splashdown], ... as in pandas.cut."""
    e, t = EVENTS, pl.col(col)
    return (
        pl.when(t <= e["launch"])
        .then(pl.lit(PHASES[0]))
        .when(t <= e["splashdown"])
        .then(pl.lit(PHASES[1]))
        .when(t <= e["well_deck"])
        .then(pl.lit(PHASES[2]))
        .when(t <= e["cargo_handover_after"])
        .then(pl.lit(PHASES[3]))
        .otherwise(pl.lit(PHASES[4]))
    )


def between(df: pl.DataFrame, start: datetime | None, end: datetime | None) -> pl.DataFrame:
    """Inclusive time slice, the same as pandas label slicing df.loc[start:end]."""
    if start is not None:
        df = df.filter(pl.col("utc") >= start)
    if end is not None:
        df = df.filter(pl.col("utc") <= end)
    return df


def fmt(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S+00:00")


def at_index(df: pl.DataFrame, col: str, fn: str) -> str:
    """Timestamp of the first max/min of a column (pandas idxmax/idxmin)."""
    i = getattr(df[col], fn)()
    return fmt(df["utc"][i])


def first_at_or_after(df: pl.DataFrame, t: datetime, col: str) -> float:
    return df.filter(pl.col("utc") >= t)[col][0]


def transient_events(
    df: pl.DataFrame,
    thr_pct: float = 1.5,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict]:
    """Short RH excursions above a 31-min rolling median, one (largest) peak per 30-min cluster.

    A bagged logger's RH moves slowly, so a sharp, decaying excursion is consistent with
    the bag or locker being handled (moist cabin air or breath reaching the sensor). It is
    not proof of an opening: there is no ground truth for what happened to the bag.
    """
    start = EVENTS["launch"] if start is None else start
    end = EVENTS["splashdown"] if end is None else end
    ex = between(
        df.select("utc", ex=pl.col("RH") - pl.col("RH").rolling_median(31, center=True)), start, end
    ).with_columns(peak=pl.col("ex").rolling_max(15, center=True, min_samples=1))
    peaks = ex.filter((pl.col("ex") > thr_pct) & (pl.col("ex") == pl.col("peak")))
    clusters: list[list[tuple[datetime, float]]] = []
    for t, v in peaks.select("utc", "ex").iter_rows():
        if clusters and (t - clusters[-1][-1][0]).total_seconds() <= 1800:
            clusters[-1].append((t, v))
        else:
            clusters.append([(t, v)])
    best = [max(c, key=lambda tv: tv[1]) for c in clusters]
    return [{"at": fmt(t), "rh_excess_pct": round(float(v), 1)} for t, v in best]


def _r(x: float, nd: int = 2) -> float:
    return round(float(x), nd)


def by_phase(df: pl.DataFrame, cols: list[str], aggs: list[str]) -> dict:
    exprs = [getattr(pl.col(c), a)().alias(f"{c}_{a}") for c in cols for a in aggs]
    g = df.group_by(phase=phase_expr()).agg(exprs).sort("phase")
    return {
        row.pop("phase"): {k: round(v, 2) for k, v in row.items()}
        for row in g.iter_rows(named=True)
    }


def analyse(dfs: dict[str, pl.DataFrame], labels: dict[str, dict]) -> dict:
    out: dict = {}
    E = EVENTS
    for sn, df in dfs.items():
        r: dict = {}
        dt = df["utc"].diff().drop_nulls().dt.total_seconds()
        r["n_records"] = df.height
        r["start_utc"] = fmt(df["utc"][0])
        r["end_utc"] = fmt(df["utc"][-1])
        r["filename_start_doy"] = FILES[sn].split("_")[1].split("-")[0]
        r["actual_start_doy"] = f"{df['utc'][0].timetuple().tm_yday:03d}"
        r["actual_end_doy"] = f"{df['utc'][-1].timetuple().tm_yday:03d}"
        r["cadence_counts"] = {str(int(k)): int(v) for k, v in dt.value_counts().iter_rows()}
        r["seq_monotonic_gapless"] = bool((df["seq"].diff().drop_nulls() == 1).all())
        # Label statistics (parsed from the PDS4 XML label) vs the data.
        r["label_vs_data"] = {
            f: {
                "label": labels[sn][f],
                "data": tuple(
                    _r(x, 3) for x in (df[f].max(), df[f].min(), df[f].mean(), df[f].std())
                ),
            }
            for f in ("T", "RH", "Td")
        }
        resid = df.select(pl.col("Td") - magnus_dewpoint(pl.col("T"), pl.col("RH")))["Td"]
        r["dewpoint_resid_C"] = {"mean": _r(resid.mean(), 3), "max_abs": _r(resid.abs().max(), 3)}
        for f in ("T", "RH"):
            steps = df[f].diff().abs()
            r[f"{f}_min_step"] = _r(steps.filter(steps > 0).min(), 4)
        r["phases"] = by_phase(df, ["T", "RH", "Td"], ["mean", "min", "max", "std"])
        margin = df.with_columns(m=pl.col("T") - pl.col("Td"))
        r["min_dewpoint_margin_C"] = _r(margin["m"].min())
        r["min_margin_at"] = at_index(margin, "m", "arg_min")
        r["abs_humidity_by_phase_gm3"] = {
            k: v["AH_mean"] for k, v in by_phase(df, ["AH"], ["mean"]).items()
        }
        d10 = df.select("utc", dT=pl.col("T").diff(10), dRH=pl.col("RH").diff(10))
        r["largest_10min_T_rise"] = {
            "dC": _r(d10["dT"].max()),
            "at": at_index(d10, "dT", "arg_max"),
        }
        r["largest_10min_T_drop"] = {
            "dC": _r(d10["dT"].min()),
            "at": at_index(d10, "dT", "arg_min"),
        }
        r["largest_10min_RH_rise"] = {
            "dpct": _r(d10["dRH"].max()),
            "at": at_index(d10, "dRH", "arg_max"),
        }
        r["T_max_at"] = at_index(df, "T", "arg_max")
        r["RH_max_at"] = at_index(df, "RH", "arg_max")
        hourly = (
            between(df, None, E["launch"])
            .group_by(h=pl.col("utc").dt.hour())
            .agg(pl.col("T").mean())
            .sort("h")
        )
        r["pad_diurnal_T_amplitude_C"] = _r(hourly["T"].max() - hourly["T"].min())
        r["pad_diurnal_T_peak_hour_utc"] = int(hourly["h"][hourly["T"].arg_max()])
        fl = between(df, E["launch"], E["splashdown"])
        hrs = ((fl["utc"] - fl["utc"][0]).dt.total_seconds() / 3600).to_numpy()
        r["flight_T_trend_C_per_day"] = _r(np.polyfit(hrs, fl["T"].to_numpy(), 1)[0] * 24, 3)
        r["flight_AH_trend_gm3_per_day"] = _r(np.polyfit(hrs, fl["AH"].to_numpy(), 1)[0] * 24, 3)
        r["flight_min_dewpoint_margin_C"] = _r((fl["T"] - fl["Td"]).min())
        r["flight_T_max"] = {"C": _r(fl["T"].max()), "at": at_index(fl, "T", "arg_max")}
        # Time-based windows, right-closed (t - w, t], as pandas rolling("12h").
        roll = fl.with_columns(
            t12=pl.col("T").rolling_mean_by("utc", window_size="12h"),
            rng4h=pl.col("T").rolling_max_by("utc", window_size="4h")
            - pl.col("T").rolling_min_by("utc", window_size="4h"),
        )
        r["flight_T_12h_mean_max"] = {
            "C": _r(roll["t12"].max()),
            "window_end": at_index(roll, "t12", "arg_max"),
        }
        r["T_mean_last_30min_before_splashdown"] = _r(
            between(fl, E["splashdown"] - timedelta(minutes=30), None)["T"].mean()
        )
        # Flyby: 2026-04-06 22:00 to 04-07 02:00 brackets closest approach and the eclipse.
        fb = between(df, _ts("2026-04-06 22:00"), _ts("2026-04-07 02:00"))
        r["flyby_window_22_02"] = {
            "T_min": _r(fb["T"].min()),
            "T_max": _r(fb["T"].max()),
            "RH_min": _r(fb["RH"].min()),
            "RH_max": _r(fb["RH"].max()),
        }
        r["flight_4h_T_range_median_C"] = _r(
            between(roll, fl["utc"][0] + timedelta(hours=4), None)["rng4h"].median()
        )
        out[sn] = r

    # Inter-logger comparison on a common minute grid (one sample per minute per logger).
    def minute(sn: str) -> pl.DataFrame:
        return dfs[sn].select(pl.col("utc").dt.truncate("1m"), "T", "RH", "AH")

    j = minute("SN1104").join(minute("SN1105"), on="utc", suffix="_1105").sort("utc")
    d = j.select("utc", *[(pl.col(f"{c}_1105") - pl.col(c)).alias(c) for c in ("T", "RH", "AH")])
    g = d.group_by(phase=phase_expr()).agg(pl.col("T", "RH", "AH").mean()).sort("phase")
    out["diff_1105_minus_1104_by_phase"] = {
        row.pop("phase"): {k: round(v, 2) for k, v in row.items()}
        for row in g.iter_rows(named=True)
    }
    dpad = between(d, None, E["launch"])
    out["pad_single_minute_max_abs_diff"] = {
        "T": _r(dpad["T"].abs().max()),
        "RH": _r(dpad["RH"].abs().max()),
    }
    jf = between(j, E["launch"], E["splashdown"])
    out["flight_T_correlation"] = _r(
        np.corrcoef(jf["T"].to_numpy(), jf["T_1105"].to_numpy())[0, 1], 3
    )

    # FD09 relocation of SN1105 (documented window 18:00-21:00 UTC on 04-09).
    w0, w1 = E["sn1105_move_window_start"], E["sn1105_move_window_end"]
    six = timedelta(hours=6)
    fd09: dict = {"window": [fmt(w0), fmt(w1)]}
    for sn, df in dfs.items():
        before = between(df, w0 - six + 30 * MIN, w0 + 30 * MIN)["T"].mean()
        after = between(df, w1 - 90 * MIN, w1 + six - 90 * MIN)["T"].mean()
        fd09[sn] = {
            "T_mean_6h_before": _r(before),
            "T_mean_6h_after": _r(after),
            "transients_in_window_thr1": transient_events(df, 1.0, w0, w1),
        }
    fd09["difference_of_changes_C"] = _r(
        (fd09["SN1105"]["T_mean_6h_after"] - fd09["SN1105"]["T_mean_6h_before"])
        - (fd09["SN1104"]["T_mean_6h_after"] - fd09["SN1104"]["T_mean_6h_before"])
    )
    e = dfs["SN1104"].with_columns(dRH=pl.col("RH").diff())
    win = between(e, _ts("2026-04-09 19:40"), _ts("2026-04-09 20:00"))
    pk = win["utc"][win["RH"].arg_max()]
    pre = between(e, pk - 5 * MIN, pk - MIN)
    after_pk = between(e, pk, None)
    settled = after_pk.filter((pl.col("RH") - pre["RH"].mean()).abs() < 1.0)["utc"][0]
    fd09["locker_E_event"] = {
        "peak_at": fmt(pk),
        "RH_jump_vs_prev_min": _r(e.filter(pl.col("utc") == pk)["dRH"][0]),
        "T_pre": _r(pre["T"].mean()),
        "T_max_within_5min": _r(between(e, pk, pk + 5 * MIN)["T"].max()),
        "T_at_plus_15min": _r(first_at_or_after(e, pk + 15 * MIN, "T")),
        "AH_pre": _r(pre["AH"].mean()),
        "AH_peak": _r(e.filter(pl.col("utc") == pk)["AH"][0]),
        "AH_at_plus_20min": _r(first_at_or_after(e, pk + 20 * MIN, "AH")),
        "minutes_until_RH_within_1pct_of_pre": int(
            settled.timestamp() // 60 - pk.timestamp() // 60
        ),
    }
    f = dfs["SN1105"].with_columns(dRH=pl.col("RH").diff())
    fd09["SN1105_RH_change_within_2min_of_locker_E_peak"] = _r(
        between(f, pk - MIN, pk + 2 * MIN)["dRH"].max()
    )
    out["fd09_relocation"] = fd09

    # Splashdown / recovery humidity.
    sp: dict = {}
    for sn, df in dfs.items():
        base = between(df, E["splashdown"] - timedelta(hours=1), E["splashdown"])["AH"]
        post = between(df, E["splashdown"], None)
        onset = post.filter(pl.col("AH") > base.mean() + 5 * base.std())
        ge7, ge10 = post.filter(pl.col("AH") >= 7), post.filter(pl.col("AH") >= 10)
        sp[sn] = {
            "AH_mean_hour_before_splashdown": _r(base.mean()),
            "AH_onset_5sigma_at": fmt(onset["utc"][0]) if onset.height else None,
            "AH_at_power_down": _r(first_at_or_after(df, E["orion_power_down"], "AH")),
            "AH_at_splash_plus_2h": _r(
                first_at_or_after(df, E["splashdown"] + timedelta(hours=2), "AH")
            ),
            "AH_at_splash_plus_8h": _r(
                first_at_or_after(df, E["splashdown"] + timedelta(hours=8), "AH")
            ),
            "first_AH_ge_7_at": fmt(ge7["utc"][0]) if ge7.height else None,
            "first_AH_ge_10_at": fmt(ge10["utc"][0]) if ge10.height else None,
        }
    out["splashdown_humidity"] = sp

    # Reentry RH step: threshold = 5x the std of 2-min RH changes in splashdown-60..-15 min.
    out["reentry_rh_step"] = {}
    for sn, df in dfs.items():
        d2 = df.select("utc", d2=pl.col("RH").diff(2))
        noise = between(d2, E["splashdown"] - 60 * MIN, E["splashdown"] - 15 * MIN)["d2"].std()
        hit = between(d2, E["splashdown"] - 15 * MIN, E["splashdown"]).filter(
            pl.col("d2") > 5 * noise
        )
        first = hit["utc"][0] if hit.height else None
        out["reentry_rh_step"][sn] = {
            "noise_std_pct": _r(noise, 3),
            "threshold_pct": _r(5 * noise, 3),
            "first_hit_at": fmt(first) if first else None,
            "step_pct": _r(hit["d2"][0], 2) if first else None,
            "minutes_before_splashdown": _r((E["splashdown"] - first).total_seconds() / 60, 1)
            if first
            else None,
        }

    # Handling-consistent RH transients: counts by threshold and locker residency.
    periods = {
        "SN1104_locker_E": ("SN1104", E["launch"], E["splashdown"]),
        "SN1105_locker_D": ("SN1105", E["launch"], w0),
        "SN1105_locker_F": ("SN1105", w1, E["splashdown"]),
    }
    out["transient_counts"] = {
        name: {str(t): len(transient_events(dfs[sn], t, s, e_)) for t in (1.0, 1.5, 3.0)}
        for name, (sn, s, e_) in periods.items()
    }
    out["inflight_transients_thr1p5"] = {sn: transient_events(df) for sn, df in dfs.items()}
    out["inflight_transients_thr1"] = {sn: transient_events(df, 1.0) for sn, df in dfs.items()}
    return out


def flight_spectrum(df: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    # The record has no gaps at a 60 s cadence, so the samples are already a uniform grid.
    x = between(
        df, EVENTS["launch"] + timedelta(hours=6), EVENTS["splashdown"] - timedelta(hours=6)
    )["T"].to_numpy()
    x = x - np.polyval(np.polyfit(np.arange(len(x)), x, 2), np.arange(len(x)))
    f = np.fft.rfftfreq(len(x), d=60.0)
    p = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    return f[1:], p[1:]


def _naive(t: datetime) -> datetime:
    return t.replace(tzinfo=None)


def plot(dfs: dict[str, pl.DataFrame], out_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ev = {k: _naive(v) for k, v in EVENTS.items()}
    xs = {sn: df["utc"].dt.replace_time_zone(None).to_numpy() for sn, df in dfs.items()}
    colors = {"SN1104": "#2a6fdb", "SN1105": "#d9822b"}
    shade = [
        (ev["launch"], ev["splashdown"], "#e8eef9", "flight"),
        (ev["splashdown"], ev["well_deck"], "#fde9d9", "ocean"),
    ]
    marks = [
        ("launch", "launch"),
        ("closest_approach", "closest approach"),
        ("sn1105_move_window_start", "SN1105 moved"),
        ("splashdown", "splashdown"),
        ("cargo_handover_after", "handover"),
    ]

    def decorate(ax):
        for s, e, c, _ in shade:
            ax.axvspan(s, e, color=c, zorder=0)
        for k, _lbl in marks:
            ax.axvline(ev[k], color="#888", lw=0.7, ls="--", zorder=1)
        ax.grid(alpha=0.25)

    fig, axes = plt.subplots(4, 1, figsize=(13, 12), sharex=True)
    for sn, df in dfs.items():
        axes[0].plot(xs[sn], df["T"].to_numpy(), lw=0.7, color=colors[sn], label=sn)
        axes[1].plot(xs[sn], df["RH"].to_numpy(), lw=0.7, color=colors[sn])
        axes[2].plot(xs[sn], df["AH"].to_numpy(), lw=0.7, color=colors[sn])
        axes[3].plot(xs[sn], (df["T"] - df["Td"]).to_numpy(), lw=0.7, color=colors[sn])
    labels = [
        "Temperature (°C)",
        "Relative humidity (%)",
        "Absolute humidity (g/m³)",
        "T − dew point (°C)",
    ]
    for ax, lab in zip(axes, labels, strict=True):
        ax.set_ylabel(lab)
        decorate(ax)
    for k, lbl in marks:
        axes[0].text(
            ev[k], axes[0].get_ylim()[1], " " + lbl, fontsize=8, va="top", rotation=90, color="#555"
        )
    axes[0].legend(loc="lower left")
    axes[0].set_title(
        "Artemis II Orion storage lockers — HOBO MX1101 loggers (shaded: flight, ocean recovery)"
    )
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "hobo_overview.png", dpi=110)
    plt.close(fig)

    # Flight zoom.
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    s, e = EVENTS["launch"] - timedelta(hours=12), EVENTS["splashdown"] + timedelta(hours=10)
    for sn, df in dfs.items():
        z = between(df, s, e)
        zx = z["utc"].dt.replace_time_zone(None).to_numpy()
        axes[0].plot(zx, z["T"].to_numpy(), lw=0.8, color=colors[sn], label=sn)
        axes[1].plot(zx, z["AH"].to_numpy(), lw=0.8, color=colors[sn])
    axes[0].set_ylabel("Temperature (°C)")
    axes[1].set_ylabel("Absolute humidity (g/m³)")
    for ax in axes:
        decorate(ax)
        ax.axvspan(
            ev["sn1105_move_window_start"], ev["sn1105_move_window_end"], color="#f6d6d6", zorder=0
        )
    axes[0].legend()
    axes[0].set_title("Flight segment (red band: documented SN1105 relocation window, FD09)")
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "hobo_flight.png", dpi=110)
    plt.close(fig)

    # Spectrum.
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for sn, df in dfs.items():
        f, p = flight_spectrum(df)
        ax.loglog(1 / f / 3600, p, lw=0.8, color=colors[sn], label=sn)
    ax.set_xlabel("Period (hours)")
    ax.set_ylabel("Power (arb.)")
    ax.set_xlim(0.1, 100)
    ax.invert_xaxis()
    ax.legend()
    ax.grid(alpha=0.25, which="both")
    ax.set_title("In-flight temperature power spectrum (detrended)")
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "hobo_flight_spectrum.png", dpi=110)
    plt.close(fig)


def main() -> None:
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=here / "data")
    ap.add_argument("--out-dir", type=Path, default=here)
    args = ap.parse_args()
    paths = fetch(args.data_dir)
    dfs = {sn: load(csv) for sn, (csv, _xml) in paths.items()}
    labels = {sn: label_stats(xml) for sn, (_csv, xml) in paths.items()}
    res = analyse(dfs, labels)
    (args.out_dir / "figures").mkdir(parents=True, exist_ok=True)
    (args.out_dir / "hobo_results.json").write_text(json.dumps(res, indent=2, default=str))
    plot(dfs, args.out_dir)
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
