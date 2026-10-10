"""Artemis II Orion locker environment (HOBO MX1101) analysis.

Downloads the two HOBO logger tables from the PDS Geosciences Node Artemis II
Mission Bundle (released 2026-10-07) and characterises them against the
mission timeline in the Artemis II Lunar Science Data User Guide.

Usage:
    python research/artemis2/analyze_hobo.py [--data-dir DIR] [--out-dir DIR]

Requires: numpy, pandas, matplotlib. Every number quoted in README.md section 1 is
written to hobo_results.json by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd


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

# Mission timeline (UTC), from the Data User Guide sections 2 and 3.4.
EVENTS = {
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
}
EVENTS = {k: pd.Timestamp(v, tz="UTC") for k, v in EVENTS.items()}

LABEL_FIELDS = {"Temperature": "T", "Relative Humidity": "RH", "Dew Point": "Td"}


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


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = ["seq", "cdt", "T", "RH", "Td"]
    # Label: "Central Daylight Time (UTC-5)". DST runs 2026-03-08..11-01, so +5 h holds throughout.
    df["utc"] = pd.to_datetime(df["cdt"], format="%m/%d/%Y %H:%M:%S").dt.tz_localize(
        "UTC"
    ) + pd.Timedelta(hours=5)
    df = df.set_index("utc")
    # Absolute humidity (g/m^3): separates moisture added from temperature-driven RH swings.
    es = 6.112 * np.exp(17.67 * df["T"] / (df["T"] + 243.5))  # hPa
    df["AH"] = 216.7 * (df["RH"] / 100 * es) / (273.15 + df["T"])
    return df


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz="UTC")


def magnus_dewpoint(t: pd.Series, rh: pd.Series) -> pd.Series:
    # Magnus-Tetens (Alduchov & Eskridge 1996 coefficients).
    a, b = 17.625, 243.04
    g = np.log(rh / 100.0) + a * t / (b + t)
    return b * g / (a - g)


def phase(ts: pd.DatetimeIndex) -> pd.Series:
    e = EVENTS
    bins = [
        ts.min() - pd.Timedelta(1, "s"),
        e["launch"],
        e["splashdown"],
        e["well_deck"],
        e["cargo_handover_after"],
        ts.max() + pd.Timedelta(1, "s"),
    ]
    labels = [
        "1 pre-launch (pad)",
        "2 flight",
        "3 ocean / recovery",
        "4 ship, pre-handover",
        "5 post-handover",
    ]
    return pd.Series(pd.cut(ts, bins=bins, labels=labels), index=ts)


def transient_events(
    df: pd.DataFrame,
    thr_pct: float = 1.5,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> list[dict]:
    """Short RH excursions above a 31-min rolling median, one (largest) peak per 30-min cluster.

    A bagged logger's RH moves slowly, so a sharp, decaying excursion is consistent with
    the bag or locker being handled (moist cabin air or breath reaching the sensor). It is
    not proof of an opening: there is no ground truth for what happened to the bag.
    """
    start = EVENTS["launch"] if start is None else start
    end = EVENTS["splashdown"] if end is None else end
    rh = df["RH"]
    ex = (rh - rh.rolling(31, center=True).median()).loc[start:end]
    peaks = ex[(ex > thr_pct) & (ex == ex.rolling(15, center=True, min_periods=1).max())]
    clusters: list[list[tuple[pd.Timestamp, float]]] = []
    for t, v in peaks.items():
        if clusters and (t - clusters[-1][-1][0]).total_seconds() <= 1800:
            clusters[-1].append((t, v))
        else:
            clusters.append([(t, v)])
    best = [max(c, key=lambda tv: tv[1]) for c in clusters]
    return [{"at": str(t), "rh_excess_pct": round(float(v), 1)} for t, v in best]


def _r(x: float, nd: int = 2) -> float:
    return round(float(x), nd)


def analyse(dfs: dict[str, pd.DataFrame], labels: dict[str, dict]) -> dict:
    out: dict = {}
    E = EVENTS
    for sn, df in dfs.items():
        r: dict = {}
        dt = df.index.to_series().diff().dropna().dt.total_seconds()
        r["n_records"] = len(df)
        r["start_utc"] = str(df.index[0])
        r["end_utc"] = str(df.index[-1])
        r["filename_start_doy"] = FILES[sn].split("_")[1].split("-")[0]
        r["actual_start_doy"] = f"{df.index[0].dayofyear:03d}"
        r["actual_end_doy"] = f"{df.index[-1].dayofyear:03d}"
        r["cadence_counts"] = {str(int(k)): int(v) for k, v in dt.value_counts().items()}
        r["seq_monotonic_gapless"] = bool((df["seq"].diff().dropna() == 1).all())
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
        resid = df["Td"] - magnus_dewpoint(df["T"], df["RH"])
        r["dewpoint_resid_C"] = {"mean": _r(resid.mean(), 3), "max_abs": _r(resid.abs().max(), 3)}
        for f in ("T", "RH"):
            steps = df[f].diff().abs()
            r[f"{f}_min_step"] = _r(steps[steps > 0].min(), 4)
        ph = phase(df.index)
        g = (
            df.groupby(ph, observed=True)[["T", "RH", "Td"]]
            .agg(["mean", "min", "max", "std"])
            .round(2)
        )
        r["phases"] = {
            str(k): {f"{a}_{b}": v for (a, b), v in row.items()} for k, row in g.iterrows()
        }
        margin = df["T"] - df["Td"]
        r["min_dewpoint_margin_C"] = _r(margin.min())
        r["min_margin_at"] = str(margin.idxmin())
        r["abs_humidity_by_phase_gm3"] = {
            str(k): _r(v) for k, v in df["AH"].groupby(ph, observed=True).mean().items()
        }
        d10 = df[["T", "RH"]].diff(10)
        r["largest_10min_T_rise"] = {"dC": _r(d10["T"].max()), "at": str(d10["T"].idxmax())}
        r["largest_10min_T_drop"] = {"dC": _r(d10["T"].min()), "at": str(d10["T"].idxmin())}
        r["largest_10min_RH_rise"] = {"dpct": _r(d10["RH"].max()), "at": str(d10["RH"].idxmax())}
        r["T_max_at"] = str(df["T"].idxmax())
        r["RH_max_at"] = str(df["RH"].idxmax())
        pad = df.loc[: E["launch"]]
        hourly = pad["T"].groupby(pad.index.hour).mean()
        r["pad_diurnal_T_amplitude_C"] = _r(hourly.max() - hourly.min())
        r["pad_diurnal_T_peak_hour_utc"] = int(hourly.idxmax())
        fl = df.loc[E["launch"] : E["splashdown"]]
        hrs = (fl.index - fl.index[0]).total_seconds() / 3600
        r["flight_T_trend_C_per_day"] = _r(np.polyfit(hrs, fl["T"], 1)[0] * 24, 3)
        r["flight_AH_trend_gm3_per_day"] = _r(np.polyfit(hrs, fl["AH"], 1)[0] * 24, 3)
        r["flight_min_dewpoint_margin_C"] = _r((fl["T"] - fl["Td"]).min())
        r["flight_T_max"] = {"C": _r(fl["T"].max()), "at": str(fl["T"].idxmax())}
        t12 = fl["T"].rolling("12h").mean()
        r["flight_T_12h_mean_max"] = {"C": _r(t12.max()), "window_end": str(t12.idxmax())}
        r["T_mean_last_30min_before_splashdown"] = _r(
            fl.loc[E["splashdown"] - pd.Timedelta(minutes=30) :, "T"].mean()
        )
        # Flyby: 2026-04-06 22:00 to 04-07 02:00 brackets closest approach and the eclipse.
        fb = df.loc[_ts("2026-04-06 22:00") : _ts("2026-04-07 02:00")]
        r["flyby_window_22_02"] = {
            "T_min": _r(fb["T"].min()),
            "T_max": _r(fb["T"].max()),
            "RH_min": _r(fb["RH"].min()),
            "RH_max": _r(fb["RH"].max()),
        }
        rng4h = fl["T"].rolling("4h").max() - fl["T"].rolling("4h").min()
        r["flight_4h_T_range_median_C"] = _r(
            rng4h.loc[fl.index[0] + pd.Timedelta(hours=4) :].median()
        )
        out[sn] = r

    # Inter-logger comparison on a common minute grid.
    a = dfs["SN1104"][["T", "RH", "AH"]].resample("1min").mean()
    b = dfs["SN1105"][["T", "RH", "AH"]].resample("1min").mean()
    d = (b - a).dropna()
    ph = phase(d.index)
    out["diff_1105_minus_1104_by_phase"] = {
        str(k): {c: _r(v) for c, v in row.items()}
        for k, row in d.groupby(ph, observed=True).mean().iterrows()
    }
    dpad = d.loc[: E["launch"]]
    out["pad_single_minute_max_abs_diff"] = {
        "T": _r(dpad["T"].abs().max()),
        "RH": _r(dpad["RH"].abs().max()),
    }
    fl = a.join(b, lsuffix="_1104", rsuffix="_1105").dropna().loc[E["launch"] : E["splashdown"]]
    out["flight_T_correlation"] = _r(fl["T_1104"].corr(fl["T_1105"]), 3)

    # FD09 relocation of SN1105 (documented window 18:00-21:00 UTC on 04-09).
    w0, w1 = E["sn1105_move_window_start"], E["sn1105_move_window_end"]
    six = pd.Timedelta(hours=6)
    fd09: dict = {"window": [str(w0), str(w1)]}
    for sn, df in dfs.items():
        before = df.loc[
            w0 - six + pd.Timedelta(minutes=30) : w0 + pd.Timedelta(minutes=30), "T"
        ].mean()
        after = df.loc[
            w1 - pd.Timedelta(hours=1, minutes=30) : w1 + six - pd.Timedelta(hours=1, minutes=30),
            "T",
        ].mean()
        fd09[sn] = {
            "T_mean_6h_before": _r(before),
            "T_mean_6h_after": _r(after),
            "transients_in_window_thr1": transient_events(df, 1.0, w0, w1),
        }
    fd09["difference_of_changes_C"] = _r(
        (fd09["SN1105"]["T_mean_6h_after"] - fd09["SN1105"]["T_mean_6h_before"])
        - (fd09["SN1104"]["T_mean_6h_after"] - fd09["SN1104"]["T_mean_6h_before"])
    )
    e = dfs["SN1104"]
    pk = e.loc[_ts("2026-04-09 19:40") : _ts("2026-04-09 20:00"), "RH"].idxmax()
    pre = e.loc[pk - pd.Timedelta(minutes=5) : pk - pd.Timedelta(minutes=1)]
    fd09["locker_E_event"] = {
        "peak_at": str(pk),
        "RH_jump_vs_prev_min": _r(e["RH"].diff().loc[pk]),
        "T_pre": _r(pre["T"].mean()),
        "T_max_within_5min": _r(e.loc[pk : pk + pd.Timedelta(minutes=5), "T"].max()),
        "T_at_plus_15min": _r(e.loc[pk + pd.Timedelta(minutes=15) :, "T"].iloc[0]),
        "AH_pre": _r(pre["AH"].mean()),
        "AH_peak": _r(e.loc[pk, "AH"]),
        "AH_at_plus_20min": _r(e.loc[pk + pd.Timedelta(minutes=20) :, "AH"].iloc[0]),
        "minutes_until_RH_within_1pct_of_pre": int(
            (e.loc[pk:, "RH"] - pre["RH"].mean()).abs().lt(1.0).idxmax().value // 60_000_000_000
            - pk.value // 60_000_000_000
        ),
    }
    f = dfs["SN1105"]["RH"].diff()
    fd09["SN1105_RH_change_within_2min_of_locker_E_peak"] = _r(
        f.loc[pk - pd.Timedelta(minutes=1) : pk + pd.Timedelta(minutes=2)].max()
    )
    out["fd09_relocation"] = fd09

    # Splashdown / recovery humidity.
    sp: dict = {}
    for sn, df in dfs.items():
        base = df.loc[E["splashdown"] - pd.Timedelta(hours=1) : E["splashdown"], "AH"]
        post = df.loc[E["splashdown"] :, "AH"]
        onset = post[post > base.mean() + 5 * base.std()]
        sp[sn] = {
            "AH_mean_hour_before_splashdown": _r(base.mean()),
            "AH_onset_5sigma_at": str(onset.index[0]) if len(onset) else None,
            "AH_at_power_down": _r(df.loc[E["orion_power_down"] :, "AH"].iloc[0]),
            "AH_at_splash_plus_2h": _r(
                df.loc[E["splashdown"] + pd.Timedelta(hours=2) :, "AH"].iloc[0]
            ),
            "AH_at_splash_plus_8h": _r(
                df.loc[E["splashdown"] + pd.Timedelta(hours=8) :, "AH"].iloc[0]
            ),
            "first_AH_ge_7_at": str(post[post >= 7].index[0]) if (post >= 7).any() else None,
            "first_AH_ge_10_at": str(post[post >= 10].index[0]) if (post >= 10).any() else None,
        }
    out["splashdown_humidity"] = sp

    # Reentry RH step: threshold = 5x the std of 2-min RH changes in splashdown-60..-15 min.
    out["reentry_rh_step"] = {}
    for sn, df in dfs.items():
        d2 = df["RH"].diff(2)
        noise = d2.loc[
            E["splashdown"] - pd.Timedelta(minutes=60) : E["splashdown"] - pd.Timedelta(minutes=15)
        ].std()
        last = d2.loc[E["splashdown"] - pd.Timedelta(minutes=15) : E["splashdown"]]
        hit = last[last > 5 * noise]
        out["reentry_rh_step"][sn] = {
            "noise_std_pct": _r(noise, 3),
            "threshold_pct": _r(5 * noise, 3),
            "first_hit_at": str(hit.index[0]) if len(hit) else None,
            "step_pct": _r(hit.iloc[0], 2) if len(hit) else None,
            "minutes_before_splashdown": _r(
                (E["splashdown"] - hit.index[0]).total_seconds() / 60, 1
            )
            if len(hit)
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


def flight_spectrum(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    fl = df.loc[
        EVENTS["launch"] + pd.Timedelta(hours=6) : EVENTS["splashdown"] - pd.Timedelta(hours=6), "T"
    ]
    x = fl.resample("1min").mean().interpolate().to_numpy()
    x = x - np.polyval(np.polyfit(np.arange(len(x)), x, 2), np.arange(len(x)))
    f = np.fft.rfftfreq(len(x), d=60.0)
    p = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    return f[1:], p[1:]


def plot(dfs: dict[str, pd.DataFrame], out_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"SN1104": "#2a6fdb", "SN1105": "#d9822b"}
    shade = [
        (EVENTS["launch"], EVENTS["splashdown"], "#e8eef9", "flight"),
        (EVENTS["splashdown"], EVENTS["well_deck"], "#fde9d9", "ocean"),
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
            ax.axvline(EVENTS[k], color="#888", lw=0.7, ls="--", zorder=1)
        ax.grid(alpha=0.25)

    fig, axes = plt.subplots(4, 1, figsize=(13, 12), sharex=True)
    for sn, df in dfs.items():
        axes[0].plot(df.index, df["T"], lw=0.7, color=colors[sn], label=sn)
        axes[1].plot(df.index, df["RH"], lw=0.7, color=colors[sn])
        axes[2].plot(df.index, df["AH"], lw=0.7, color=colors[sn])
        axes[3].plot(df.index, df["T"] - df["Td"], lw=0.7, color=colors[sn])
    labels = [
        "Temperature (°C)",
        "Relative humidity (%)",
        "Absolute humidity (g/m³)",
        "T − dew point (°C)",
    ]
    for ax, lab in zip(axes, labels):
        ax.set_ylabel(lab)
        decorate(ax)
    for k, lbl in marks:
        axes[0].text(
            EVENTS[k],
            axes[0].get_ylim()[1],
            " " + lbl,
            fontsize=8,
            va="top",
            rotation=90,
            color="#555",
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
    s, e = EVENTS["launch"] - pd.Timedelta(hours=12), EVENTS["splashdown"] + pd.Timedelta(hours=10)
    for sn, df in dfs.items():
        z = df.loc[s:e]
        axes[0].plot(z.index, z["T"], lw=0.8, color=colors[sn], label=sn)
        axes[1].plot(z.index, z["AH"], lw=0.8, color=colors[sn])
    axes[0].set_ylabel("Temperature (°C)")
    axes[1].set_ylabel("Absolute humidity (g/m³)")
    for ax in axes:
        decorate(ax)
        ax.axvspan(
            EVENTS["sn1105_move_window_start"],
            EVENTS["sn1105_move_window_end"],
            color="#f6d6d6",
            zorder=0,
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
