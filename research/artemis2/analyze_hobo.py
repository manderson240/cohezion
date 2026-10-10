"""Artemis II Orion locker environment (HOBO MX1101) analysis.

Downloads the two HOBO logger tables from the PDS Geosciences Node Artemis II
Mission Bundle (released 2026-10-07) and characterises them against the
mission timeline in the Artemis II Lunar Science Data User Guide.

Usage:
    python research/artemis2/analyze_hobo.py [--data-dir DIR] [--out-dir DIR]

Requires: numpy, pandas, matplotlib.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd


BASE = "https://pds-geosciences.wustl.edu/artemis2/urn-nasa-pds-artemis2_mission/data_orion_environment/"
FILES = {
    "SN1104": "art002_086-162546_111-205046_hobo1104_raw_v01.csv",
    "SN1105": "art002_086-162926_111-203826_hobo1105_raw_v01.csv",
}

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

# PDS4 label Statistics blocks (max, min, mean, std) for each field.
LABEL_STATS = {
    "SN1104": {
        "T": (25.57, 17.77, 22.06, 1.75),
        "RH": (68.579, 18.27, 38.51, 16.26),
        "Td": (15.56, -2.87, 6.10, 5.32),
    },
    "SN1105": {
        "T": (27.11, 16.82, 21.81, 1.46),
        "RH": (78.14, 18.68, 35.54, 11.61),
        "Td": (17.09, -1.82, 5.23, 4.46),
    },
}


def fetch(data_dir: Path) -> dict[str, Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for sn, name in FILES.items():
        p = data_dir / name
        if not p.exists():
            with urllib.request.urlopen(BASE + name, timeout=120) as r:  # noqa: S310 -- fixed https constant
                p.write_bytes(r.read())
        paths[sn] = p
    return paths


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = ["seq", "cdt", "T", "RH", "Td"]
    # Label: "Central Daylight Time (UTC-5)".
    df["utc"] = pd.to_datetime(df["cdt"], format="%m/%d/%Y %H:%M:%S").dt.tz_localize(
        "UTC"
    ) + pd.Timedelta(hours=5)
    return df.set_index("utc")


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


def transient_events(df: pd.DataFrame, thr_pct: float = 1.5) -> list[dict]:
    """Short RH excursions above a 31-min rolling median during flight.

    A sealed locker's RH moves slowly; a sharp, decaying excursion means moist cabin air
    (or a hand/breath) got in, i.e. the locker or bag was opened.
    """
    rh = df.loc[EVENTS["launch"] : EVENTS["splashdown"], "RH"]
    ex = rh - rh.rolling(31, center=True).median()
    peaks = ex[(ex > thr_pct) & (ex == ex.rolling(15, center=True).max())]
    events: list[tuple[pd.Timestamp, float]] = []
    for t, v in peaks.items():
        if not events or (t - events[-1][0]).total_seconds() > 1800:
            events.append((t, v))
    return [{"at": str(t), "rh_excess_pct": round(float(v), 1)} for t, v in events]


def analyse(dfs: dict[str, pd.DataFrame]) -> dict:
    out: dict = {}
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
        # Label statistics check.
        r["label_vs_data"] = {
            f: {
                "label": LABEL_STATS[sn][f],
                "data": tuple(
                    round(float(x), 3)
                    for x in (df[f].max(), df[f].min(), df[f].mean(), df[f].std())
                ),
            }
            for f in ("T", "RH", "Td")
        }
        # Dew point recomputation.
        td_calc = magnus_dewpoint(df["T"], df["RH"])
        resid = df["Td"] - td_calc
        r["dewpoint_resid_C"] = {
            "mean": round(float(resid.mean()), 3),
            "max_abs": round(float(resid.abs().max()), 3),
        }
        # Quantisation (smallest non-zero step).
        for f in ("T", "RH"):
            steps = df[f].diff().abs()
            r[f"{f}_min_step"] = round(float(steps[steps > 0].min()), 4)
        # Phase statistics.
        ph = phase(df.index)
        g = (
            df.groupby(ph, observed=True)[["T", "RH", "Td"]]
            .agg(["mean", "min", "max", "std"])
            .round(2)
        )
        r["phases"] = {
            str(k): {f"{a}_{b}": v for (a, b), v in row.items()} for k, row in g.iterrows()
        }
        # Condensation margin: T - Td.
        margin = df["T"] - df["Td"]
        r["min_dewpoint_margin_C"] = round(float(margin.min()), 2)
        r["min_margin_at"] = str(margin.idxmin())
        # Absolute humidity (g/m^3) -- separates moisture added from temperature-driven RH swings.
        es = 6.112 * np.exp(17.67 * df["T"] / (df["T"] + 243.5))  # hPa
        ah = 216.7 * (df["RH"] / 100 * es) / (273.15 + df["T"])
        df["AH"] = ah
        r["abs_humidity_by_phase_gm3"] = {
            str(k): round(float(v), 2) for k, v in ah.groupby(ph, observed=True).mean().items()
        }
        # Largest 10-minute changes.
        d10 = df[["T", "RH"]].diff(10)
        r["largest_10min_T_rise"] = {
            "dC": round(float(d10["T"].max()), 2),
            "at": str(d10["T"].idxmax()),
        }
        r["largest_10min_T_drop"] = {
            "dC": round(float(d10["T"].min()), 2),
            "at": str(d10["T"].idxmin()),
        }
        r["largest_10min_RH_rise"] = {
            "dpct": round(float(d10["RH"].max()), 2),
            "at": str(d10["RH"].idxmax()),
        }
        r["T_max_at"] = str(df["T"].idxmax())
        r["RH_max_at"] = str(df["RH"].idxmax())
        # Pre-launch diurnal amplitude (pad, 24 h periodicity).
        pad = df.loc[: EVENTS["launch"]]
        hourly = pad["T"].groupby(pad.index.hour).mean()
        r["pad_diurnal_T_amplitude_C"] = round(float(hourly.max() - hourly.min()), 2)
        r["pad_diurnal_T_peak_hour_utc"] = int(hourly.idxmax())
        # In-flight drift: linear trend of T and AH during flight.
        fl = df.loc[EVENTS["launch"] : EVENTS["splashdown"]]
        hrs = (fl.index - fl.index[0]).total_seconds() / 3600
        r["flight_T_trend_C_per_day"] = round(float(np.polyfit(hrs, fl["T"], 1)[0] * 24), 3)
        r["flight_AH_trend_gm3_per_day"] = round(float(np.polyfit(hrs, fl["AH"], 1)[0] * 24), 3)
        out[sn] = r

    # Inter-logger comparison on a common minute grid.
    a = dfs["SN1104"][["T", "RH", "AH"]].resample("1min").mean()
    b = dfs["SN1105"][["T", "RH", "AH"]].resample("1min").mean()
    d = (b - a).dropna()
    ph = phase(d.index)
    out["diff_1105_minus_1104_by_phase"] = {
        str(k): {c: round(float(v), 2) for c, v in row.items()}
        for k, row in d.groupby(ph, observed=True).mean().iterrows()
    }
    # SN1105 relocation: locate step change in the T/RH difference around the documented window.
    w = d.loc["2026-04-09 12:00":"2026-04-10 03:00"]
    roll = w["T"].rolling(30, center=True).mean()
    step = (roll.shift(-30) - roll.shift(30)).abs()
    out["sn1105_move_step_time_estimate"] = str(step.idxmax()) if step.notna().any() else None
    out["sn1105_move_step_dT"] = round(float(step.max()), 2) if step.notna().any() else None
    # Reentry: first minute in the final hour before splashdown where RH jumps >0.35 %/2 min (pre-step noise <0.1).
    out["reentry_rh_step"] = {}
    for sn, df in dfs.items():
        w = df.loc[EVENTS["splashdown"] - pd.Timedelta(hours=1) : EVENTS["splashdown"], "RH"].diff(
            2
        )
        hit = w[w > 0.35]
        out["reentry_rh_step"][sn] = (
            {
                "at": str(hit.index[0]),
                "minutes_before_splashdown": round(
                    (EVENTS["splashdown"] - hit.index[0]).total_seconds() / 60, 1
                ),
            }
            if len(hit)
            else None
        )
    out["inflight_locker_access_events"] = {sn: transient_events(df) for sn, df in dfs.items()}
    corr = a.join(b, lsuffix="_1104", rsuffix="_1105").dropna()
    fl = corr.loc[EVENTS["launch"] : EVENTS["splashdown"]]
    out["flight_T_correlation"] = round(float(fl["T_1104"].corr(fl["T_1105"])), 3)
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
    dfs = {sn: load(p) for sn, p in paths.items()}
    res = analyse(dfs)
    (args.out_dir / "figures").mkdir(parents=True, exist_ok=True)
    (args.out_dir / "hobo_results.json").write_text(json.dumps(res, indent=2, default=str))
    plot(dfs, args.out_dir)
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
