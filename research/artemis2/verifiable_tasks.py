"""Build tool-dependent, deterministically verifiable questions from the Artemis II PDS release.

The construction follows Stage II of Axion 1.0 (arXiv:2611.03233, section on tool-dependent
reasoning): filter real records by a condition, select ONE entity by an extreme value that must
beat the runner-up by a stated margin, compute a derived quantity with a fixed formula, and keep
the reference answer fixed while the question is worded around it. Two checks from the paper are
applied here:

  * unambiguity: a candidate whose winner does not clear the margin is rejected, not kept;
  * independent implementations: every answer is computed twice, once with polars and once with
    the standard library only (``csv`` + ``datetime``), and the task is rejected unless both agree.

The paper's third check, a closed-book probe that drops questions a model answers without tools,
needs a model to run, so it is NOT run here and each task records that. The source data was first
released on 2026-10-07, so a model trained before then cannot have seen these answers.

Inputs: the two HOBO logger files (downloaded and MD5-checked by ``analyze_hobo.fetch``) and a
directory holding the mission-audio transcript CSVs (``*_trn-csv_v01.csv``).

Usage:
    python research/artemis2/verifiable_tasks.py TRANSCRIPT_DIR [--data-dir DIR] [--out PATH]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from itertools import pairwise
from pathlib import Path

import polars as pl


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_hobo as hobo  # noqa: E402 -- sibling script, not a package
import transcripts as trn  # noqa: E402


LAUNCH = hobo.EVENTS["launch"]
SPLASHDOWN = hobo.EVENTS["splashdown"]
CREW = ("Wiseman", "Glover", "Koch", "Hansen")
LOOPS_FILE = re.compile(r"_oe\d_trn-csv")
AUDIO_BASE = (
    "https://d1ejlg980osaur.cloudfront.net/archive/artemis/artemis2/artemis2_mission_audio/"
)
REL_TOL = 1e-6  # the two implementations must agree to this relative tolerance
PROBE = "not run: needs a model; data first public 2026-10-07"


# ---------------------------------------------------------------------------------------------
# Independent standard-library readers. They deliberately share no code with analyze_hobo.py or
# transcripts.py, so a parsing bug in one implementation does not repeat in the other.


def std_hobo(path: Path) -> list[tuple[datetime, float, float]]:
    """(utc, T degC, RH %) rows. The file's clock is CDT, i.e. UTC-5, for the whole record."""
    rows = []
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        next(reader)
        for rec in reader:
            local = datetime.strptime(rec[1], "%m/%d/%Y %H:%M:%S")
            rows.append(
                ((local + timedelta(hours=5)).replace(tzinfo=UTC), float(rec[2]), float(rec[3]))
            )
    rows.sort()
    return rows


def std_abs_humidity(t: float, rh: float) -> float:
    """Absolute humidity in g/m^3 from the Magnus saturation pressure (hPa)."""
    return 216.7 * (rh / 100 * 6.112 * math.exp(17.67 * t / (t + 243.5))) / (273.15 + t)


def std_transcripts(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.rglob("*_trn-csv_v01.csv")):
        with path.open(newline="", encoding="utf-8") as fh:
            for i, rec in enumerate(csv.DictReader(fh)):
                rows.append({
                    "file": path.name, "row": i,
                    "audio_time": rec["audio_time"] or "", "utc": rec["utc"] or "",
                    "speaker": (rec["speaker"] or "").strip(), "text": rec["text"] or "",
                })  # fmt: skip
    return rows


def std_utc(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return None


def words(text: str) -> int:
    """Spoken words: editorial [[...]] annotations removed, then whitespace-split."""
    return len(re.sub(r"\[\[.*?\]\]", " ", text).split())


# ---------------------------------------------------------------------------------------------
# Task construction


def pick(scores: dict[str, float], margin: float, relative: bool) -> tuple[str, str | None, bool]:
    """Winner, runner-up, and whether the winner clears the margin over the runner-up."""
    ranked = sorted(scores, key=scores.get, reverse=True)
    if len(ranked) < 2:
        return ranked[0], None, True
    top, second = scores[ranked[0]], scores[ranked[1]]
    gap = (top - second) / abs(second) if relative and second else top - second
    return ranked[0], ranked[1], gap >= margin


def agree(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=1e-9)


def make_task(spec: dict, primary: tuple[dict, float], independent: tuple[dict, float]) -> dict:
    """Combine both implementations' results into one task record, or one rejection record."""
    (scores_a, answer_a), (scores_b, answer_b) = primary, independent
    winner_a, runner_a, clear_a = pick(scores_a, spec["margin"], spec["relative_margin"])
    winner_b, _, clear_b = pick(scores_b, spec["margin"], spec["relative_margin"])
    reasons = []
    if winner_a != winner_b:
        reasons.append(f"implementations pick different entities: {winner_a} vs {winner_b}")
    if not agree(answer_a, answer_b):
        reasons.append(f"implementations disagree on the answer: {answer_a} vs {answer_b}")
    agreed = not reasons
    if not (clear_a and clear_b):
        reasons.append("winner does not clear the margin over the runner-up")
    record = {
        "id": spec["id"],
        "question": spec["question"],
        "answer": round(answer_a, spec["decimals"]),
        "unit": spec["unit"],
        "tolerance": spec["tolerance"],
        "selected_entity": winner_a,
        "runner_up": runner_a,
        "selection_scores": {k: round(v, 4) for k, v in scores_a.items()},
        "margin_rule": ("relative " if spec["relative_margin"] else "absolute ")
        + str(spec["margin"]),
        "sources": spec["sources"],
        "checks": {"two_implementations_agree": agreed, "closed_book_probe": PROBE},
    }
    if reasons:
        record["rejected_because"] = reasons
    return record


# --- HOBO locker loggers ---------------------------------------------------------------------


def hobo_sources() -> list[str]:
    return [hobo.BASE + f"{b}.csv" for b in hobo.FILES.values()]


def flight_pl(df: pl.DataFrame) -> pl.DataFrame:
    return df.filter((pl.col("utc") >= LAUNCH) & (pl.col("utc") <= SPLASHDOWN))


def flight_std(rows: list) -> list:
    return [r for r in rows if LAUNCH <= r[0] <= SPLASHDOWN]


def task_rh_jump(dfs: dict[str, pl.DataFrame], raw: dict[str, list]) -> dict:
    """Largest one-minute RH rise in flight; answer = temperature at that minute."""

    def primary():
        scores, temps = {}, {}
        for sn, df in dfs.items():
            d = flight_pl(df).with_columns(jump=pl.col("RH").diff())
            i = d["jump"].arg_max()
            scores[sn], temps[sn] = d["jump"][i], d["T"][i]
        return scores, temps[max(scores, key=scores.get)]

    def independent():
        scores, temps = {}, {}
        for sn, rows in raw.items():
            f = flight_std(rows)
            jump, t = max((b[2] - a[2], b[1]) for a, b in pairwise(f))
            scores[sn], temps[sn] = jump, t
        return scores, temps[max(scores, key=scores.get)]

    return make_task(
        {
            "id": "hobo-rh-jump-temperature",
            "question": (
                "Two HOBO MX1101 loggers (serials 1104 and 1105) rode in Orion's storage lockers on "
                "Artemis II and logged temperature and relative humidity once a minute; their raw "
                "files are in the PDS artemis2_mission bundle, collection data_orion_environment. "
                "Between launch (2026-04-01 22:35:12 UTC) and splashdown (2026-04-11 00:07:00 UTC), "
                "find the logger whose relative humidity rose the most from one sample to the next. "
                "What temperature, in degrees C, did that logger record at the sample where that "
                "largest rise ended? The file clock is Central Daylight Time (UTC-5)."
            ),
            "unit": "degC", "tolerance": 0.01, "decimals": 2,
            "margin": 1.0, "relative_margin": True,  # winner's jump at least double the other's
            "sources": hobo_sources(),
        },
        primary(), independent(),
    )  # fmt: skip


def task_flight_abs_humidity(dfs: dict[str, pl.DataFrame], raw: dict[str, list]) -> dict:
    """Warmer logger in flight; answer = its mean absolute humidity in flight."""

    def primary():
        f = {sn: flight_pl(df) for sn, df in dfs.items()}
        scores = {sn: d["T"].mean() for sn, d in f.items()}
        return scores, f[max(scores, key=scores.get)]["AH"].mean()

    def independent():
        f = {sn: flight_std(rows) for sn, rows in raw.items()}
        scores = {sn: sum(r[1] for r in rows) / len(rows) for sn, rows in f.items()}
        warm = f[max(scores, key=scores.get)]
        return scores, sum(std_abs_humidity(r[1], r[2]) for r in warm) / len(warm)

    return make_task(
        {
            "id": "hobo-warmer-logger-absolute-humidity",
            "question": (
                "Using the two Artemis II HOBO locker-logger files in the PDS artemis2_mission "
                "bundle (data_orion_environment; serials 1104 and 1105, one sample a minute, clock "
                "in CDT = UTC-5), take only samples from launch (2026-04-01 22:35:12 UTC) to "
                "splashdown (2026-04-11 00:07:00 UTC). Pick the logger with the higher mean "
                "temperature over that span. What was its mean absolute humidity over the same "
                "samples, in g/m^3? Compute absolute humidity per sample as "
                "216.7 * (RH/100 * 6.112 * exp(17.67*T/(T+243.5))) / (273.15+T), then average."
            ),
            "unit": "g/m^3", "tolerance": 0.01, "decimals": 3,
            "margin": 0.5, "relative_margin": False,  # degC between the two flight means
            "sources": hobo_sources(),
        },
        primary(), independent(),
    )  # fmt: skip


def task_daily_range(dfs: dict[str, pl.DataFrame], raw: dict[str, list]) -> dict:
    """SN1105: whole UTC flight day with the widest temperature range; answer = that range."""
    days = [date(2026, 4, d) for d in range(2, 11)]  # whole UTC days between launch and splashdown

    def primary():
        d = (
            dfs["SN1105"]
            .with_columns(day=pl.col("utc").dt.date())
            .filter(pl.col("day").is_in(days))
            .group_by("day")
            .agg(rng=pl.col("T").max() - pl.col("T").min())
        )
        scores = {str(r["day"]): r["rng"] for r in d.to_dicts()}
        return scores, max(scores.values())

    def independent():
        by_day = defaultdict(list)
        for t, temp, _rh in raw["SN1105"]:
            if t.date() in days:
                by_day[t.date()].append(temp)
        scores = {str(k): max(v) - min(v) for k, v in by_day.items()}
        return scores, max(scores.values())

    return make_task(
        {
            "id": "hobo-1105-widest-daily-temperature-range",
            "question": (
                "In the Artemis II PDS release, HOBO logger serial 1105 (artemis2_mission bundle, "
                "data_orion_environment; clock in CDT = UTC-5) recorded locker temperature every "
                "minute. Considering only whole UTC calendar days 2026-04-02 through 2026-04-10, "
                "which day had the largest difference between its highest and lowest temperature "
                "sample, and what was that difference in degrees C?"
            ),
            "unit": "degC", "tolerance": 0.01, "decimals": 2,
            "margin": 0.1, "relative_margin": False,
            "sources": hobo_sources()[1:],
        },
        primary(), independent(),
    )  # fmt: skip


# --- Mission-audio transcripts ---------------------------------------------------------------


def loops_sources(df: pl.DataFrame) -> list[str]:
    names = df.filter(pl.col("file").str.contains(LOOPS_FILE.pattern))["file"].unique().sort()
    return [AUDIO_BASE + "data_transcripts_loops/" + n for n in names]


def task_crew_rows_on_day(df: pl.DataFrame, raw: list[dict]) -> dict:
    """Crew member with the most voice-loop rows stamped 2026-04-07; answer = that count."""

    def primary():
        d = (
            df.filter(pl.col("file").str.contains(LOOPS_FILE.pattern))
            .with_columns(spk=pl.col("speaker").str.strip_chars())
            .filter(pl.col("spk").is_in(CREW) & pl.col("utc").str.starts_with("2026-04-07 "))
        )
        scores = {r["spk"]: float(r["len"]) for r in d.group_by("spk").len().to_dicts()}
        return scores, max(scores.values())

    def independent():
        c = Counter(
            r["speaker"]
            for r in raw
            if LOOPS_FILE.search(r["file"])
            and r["speaker"] in CREW
            and r["utc"].startswith("2026-04-07 ")
        )
        return {k: float(v) for k, v in c.items()}, float(max(c.values()))

    return make_task(
        {
            "id": "loops-crew-rows-2026-04-07",
            "question": (
                "The Artemis II PDS mission-audio bundle (artemis2_mission_audio) has voice-loop "
                "transcripts in collection data_transcripts_loops: CSV files with columns "
                "audio_time,utc,speaker,text. Counting only rows whose utc stamp falls on "
                "2026-04-07 and whose speaker (ignoring surrounding spaces) is one of the four "
                "crew members Wiseman, Glover, Koch or Hansen, which crew member has the most "
                "rows, and how many?"
            ),
            "unit": "rows", "tolerance": 0, "decimals": 0,
            "margin": 0.1, "relative_margin": True,
            "sources": loops_sources(df),
        },
        primary(), independent(),
    )  # fmt: skip


def task_crew_words(df: pl.DataFrame, raw: list[dict]) -> dict:
    """Crew member with the most spoken words across all transcripts; answer = that total."""

    def primary():
        d = (
            df.with_columns(spk=pl.col("speaker").str.strip_chars())
            .filter(pl.col("spk").is_in(CREW))
            .with_columns(
                n=pl.col("text").str.replace_all(r"\[\[.*?\]\]", " ").str.split(" ")
                .list.eval(pl.element().filter(pl.element().str.strip_chars() != "")).list.len()
            )
        )  # fmt: skip
        scores = {
            r["spk"]: float(r["n"]) for r in d.group_by("spk").agg(pl.col("n").sum()).to_dicts()
        }
        return scores, max(scores.values())

    def independent():
        totals = Counter()
        for r in raw:
            if r["speaker"] in CREW:
                totals[r["speaker"]] += words(r["text"])
        return {k: float(v) for k, v in totals.items()}, float(max(totals.values()))

    return make_task(
        {
            "id": "transcripts-crew-word-count",
            "question": (
                "Across every transcript CSV in the Artemis II PDS mission-audio bundle (both the "
                "data_transcripts_loops and data_transcripts_pcd collections; columns "
                "audio_time,utc,speaker,text), which of the four crew members (Wiseman, Glover, "
                "Koch, Hansen; ignore spaces around the speaker name) has the most words of "
                "transcribed speech, and how many? Remove editorial annotations written in double "
                "square brackets [[...]] before counting, and count whitespace-separated words."
            ),
            "unit": "words", "tolerance": 0, "decimals": 0,
            "margin": 0.05, "relative_margin": True,
            "sources": [AUDIO_BASE + "data_transcripts_loops/", AUDIO_BASE + "data_transcripts_pcd/"],
        },
        primary(), independent(),
    )  # fmt: skip


def task_largest_cut(df: pl.DataFrame, raw: list[dict]) -> dict:
    """Voice-loop file with the longest removed stretch of audio; answer = minutes removed."""

    def primary():
        cuts = trn.loop_gaps(df)["cuts"]
        scores = {}
        for c in cuts:
            scores[c["file"]] = max(scores.get(c["file"], 0.0), c["removed_min"])
        # loop_gaps rounds to 0.1 min; recompute the winner's value unrounded from its endpoints
        best = max(cuts, key=lambda c: c["removed_min"])
        rows = df.filter(pl.col("file") == best["file"]).with_columns(
            t=pl.col("utc").str.to_datetime("%Y-%m-%d %H:%M:%S%.f", strict=False)
        )
        rows = rows.filter(pl.col("t").is_not_null()).with_columns(
            off=pl.col("t").dt.epoch("ms") / 1000 - trn._clock_s("audio_time")
        )
        jump = rows.sort("row")["off"].diff().max() / 60
        return scores, jump

    def independent():
        by_file = defaultdict(list)
        for r in raw:
            t = std_utc(r["utc"])
            if LOOPS_FILE.search(r["file"]) and t is not None:
                h, m, s = (float(x) for x in r["audio_time"].split(":"))
                off = (t - datetime(1970, 1, 1)).total_seconds() - (h * 3600 + m * 60 + s)
                by_file[r["file"]].append((r["row"], off))
        scores, exact = {}, {}
        for name, seq in by_file.items():
            seq.sort()
            jumps = [b[1] - a[1] for a, b in pairwise(seq)]
            big = [j for j in jumps if abs(j) > trn.CUT_S]
            if big:
                exact[name] = max(big) / 60
                scores[name] = round(exact[name], 1)
        return scores, exact[max(exact, key=exact.get)]

    return make_task(
        {
            "id": "loops-longest-removed-audio",
            "question": (
                "Each Artemis II voice-loop transcript in the PDS artemis2_mission_audio bundle "
                "(collection data_transcripts_loops) gives two clocks per row: audio_time, a "
                "position in a stitched recording, and utc, wall-clock time. While the recording "
                "runs continuously, utc minus audio_time stays constant; a jump between consecutive "
                "rows of more than 60 seconds means audio was cut out. Which transcript file has "
                "the largest such jump, and how many minutes of audio does it remove? Ignore rows "
                "whose utc stamp is not a full date and time."
            ),
            "unit": "minutes", "tolerance": 0.05, "decimals": 2,
            "margin": 0.05, "relative_margin": True,
            "sources": loops_sources(df),
        },
        primary(), independent(),
    )  # fmt: skip


def build(data_dir: Path, transcript_dir: Path) -> dict:
    paths = hobo.fetch(data_dir)
    dfs = {sn: hobo.load(csv_path) for sn, (csv_path, _xml) in paths.items()}
    raw_hobo = {sn: std_hobo(csv_path) for sn, (csv_path, _xml) in paths.items()}
    tdf = trn.load(transcript_dir)
    raw_t = std_transcripts(transcript_dir)
    records = [
        task_rh_jump(dfs, raw_hobo),
        task_flight_abs_humidity(dfs, raw_hobo),
        task_daily_range(dfs, raw_hobo),
        task_crew_rows_on_day(tdf, raw_t),
        task_crew_words(tdf, raw_t),
        task_largest_cut(tdf, raw_t),
    ]
    return {
        "method": "Axion 1.0 (arXiv:2611.03233) Stage II construction: filter, unique extreme "
        "with margin, deterministic derived quantity; verified by two independent "
        "implementations (polars and standard library)",
        "tasks": [r for r in records if "rejected_because" not in r],
        "rejected": [r for r in records if "rejected_because" in r],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("transcripts", type=Path)
    ap.add_argument("--data-dir", type=Path, default=HERE / "data")
    ap.add_argument("--out", type=Path, default=HERE / "verifiable_tasks.json")
    args = ap.parse_args()
    result = build(args.data_dir, args.transcripts)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    for r in result["tasks"]:
        print(f"OK   {r['id']}: {r['selected_entity']} -> {r['answer']} {r['unit']}")
    for r in result["rejected"]:
        print(f"DROP {r['id']}: {'; '.join(r['rejected_because'])}")


if __name__ == "__main__":
    main()
