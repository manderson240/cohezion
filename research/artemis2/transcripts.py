"""Artemis II mission-audio transcripts: statistics, quality checks and a verified event list.

Input: the two transcript collections of the PDS ``artemis2_mission_audio`` bundle
(``data_transcripts_loops`` and ``data_transcripts_pcd``), downloaded locally. Every
``*_trn-csv_v01.csv`` file has the header ``audio_time,utc,speaker,text``.

Output: ``transcript_events.json``. It holds per-file counts, speakers, quality findings and
EVENTS. EVENTS is a curated list of flash call-outs, spacecraft events and lunar observations.
Each entry gives a UTC stamp and a text fragment, and the script requires that fragment to
appear verbatim in a row with that stamp. If any quote fails to match, the script exits non-zero.
So the write-up can only quote what the archive actually says.

Usage:
    python research/artemis2/transcripts.py TRANSCRIPT_DIR [--out PATH]

TRANSCRIPT_DIR is searched recursively for ``*_trn-csv_v01.csv``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from itertools import pairwise
from pathlib import Path

import polars as pl


# (utc prefix, verbatim fragment, category, short label)
EVENTS: list[tuple[str, str, str, str]] = [
    # --- impact-flash call-outs during the eclipse (crew tablet PCD3 + voice loop) ---
    (
        "2026-04-07 00:41:00",
        "I just saw a meteor -- I just saw a flash!",
        "flash",
        "Wiseman: first call",
    ),
    (
        "2026-04-07 00:42:33",
        "No, streaks.",
        "flash",
        "Wiseman: asked flash or streak, answers streaks",
    ),
    ("2026-04-07 00:51:15", "100 percent just saw a meteorite", "flash", "Wiseman"),
    (
        "2026-04-07 00:51:37",
        "Reid reports he's seen two meteors",
        "flash",
        "Glover relays to Earth",
    ),
    ("2026-04-07 00:51:38", "it's just like a bloop", "flash", "Hansen describes"),
    ("2026-04-07 00:51:57", "We saw an impact flash.", "flash", "Hansen"),
    (
        "2026-04-07 00:52:52",
        "I think I just saw another one, but this one I'm less sure of",
        "flash",
        "Hansen",
    ),
    ("2026-04-07 00:59:10", "We have seen three impact flashes so far.", "flash", "Wiseman tally"),
    ("2026-04-07 00:59:18", "I just saw another one.", "flash", "Hansen"),
    (
        "2026-04-07 01:00:32",
        "hearing you saw them on the near side",
        "flash",
        "science team interpretation",
    ),
    ("2026-04-07 01:03:04", "I just saw another one.", "flash", "Wiseman"),
    (
        "2026-04-07 01:17:32",
        "I have not seen an impact flash in the last five minutes.",
        "flash",
        "Wiseman",
    ),
    ("2026-04-07 01:17:49", "I think I just saw one.", "flash", "Wiseman"),
    (
        "2026-04-07 01:17:59",
        "right near the South Pole on the Terminator, Reid just saw one",
        "flash",
        "Glover relays position",
    ),
    ("2026-04-07 01:18:25", "I saw one in the upper right quadrant.", "flash", "Wiseman position"),
    ("2026-04-07 19:05:44", "It's a pinprick of light.", "flash", "Hansen next-day debrief"),
    (
        "2026-04-07 19:06:46",
        "galactic cosmic",
        "flash",
        "Wiseman contrasts with cosmic-ray flashes",
    ),
    # --- spacecraft events ---
    (
        "2026-04-06 00:09:20",
        "warning cabin leak suspected",
        "spacecraft",
        "cabin leak alarm during suit drying",
    ),
    (
        "2026-04-06 01:05:31",
        "it registered a pressure change",
        "spacecraft",
        "cause: lower cabin fan speed",
    ),
    (
        "2026-04-06 01:07:19",
        "what happened with S-band string 2",
        "spacecraft",
        "S-band string 2 issue",
    ),
    (
        "2026-04-06 02:16:50",
        "PCD 3, the Lunar Targeting Package, when I double click on it",
        "spacecraft",
        "PCD3 cannot open LTP",
    ),
    ("2026-04-06 03:09:41", "Hooray, that fixed it.", "spacecraft", "PCD3 fixed"),
    (
        "2026-04-06 04:22:11",
        "One said for HCN, it was like a read error.",
        "spacecraft",
        "air analyser alarm",
    ),
    (
        "2026-04-06 21:15:16",
        "we were about to die on this PCD",
        "spacecraft",
        "PCD charge cord unplugged",
    ),
    (
        "2026-04-06 21:16:01",
        "we have a temperature constraint on the windows",
        "spacecraft",
        "window too warm",
    ),
    (
        "2026-04-06 23:40:53",
        "We experienced some blockage from a solar array.",
        "spacecraft",
        "comm blockage after AOS",
    ),
    (
        "2026-04-07 01:28:41",
        "Saw three camera temperature low.",
        "spacecraft",
        "SAW3 camera cold caution",
    ),
    (
        "2026-04-07 01:32:29",
        "It just got a little cool during the eclipse.",
        "spacecraft",
        "Houston: SAW3 cold, no action",
    ),
    (
        "2026-04-07 03:13:15",
        "We believe this is a recurrence of what we saw with DU-2",
        "spacecraft",
        "display unit caution",
    ),
    (
        "2026-04-07 22:31:26",
        "we're suspecting interference from that cable",
        "spacecraft",
        "smoke detector noise",
    ),
    (
        "2026-04-07 22:38:06",
        "we have seen the spikes return",
        "spacecraft",
        "smoke detector noise returns",
    ),
    (
        "2026-04-07 23:48:44",
        "Integrity optocoupler glitch.",
        "spacecraft",
        "prop caution and warning",
    ),
    (
        "2026-04-07 23:51:00",
        "It's something internal to the prop system",
        "spacecraft",
        "not an optocoupler glitch",
    ),
    (
        "2026-04-07 23:56:45",
        "We thought we had inhibited the fitter. Evidently not.",
        "spacecraft",
        "branch swap",
    ),
    # --- other observations ---
    (
        "2026-04-07 00:29:09",
        "I think these are debris hits, man.",
        "observation",
        "Hansen, window in grazing sunlight",
    ),
    ("2026-04-07 00:29:32", "It's like it came in deep, man.", "observation", "Hansen"),
    ("2026-04-07 00:29:43", "That's not a nick.", "observation", "Hansen"),
    (
        "2026-04-06 18:00:44",
        "And we would like to call it CARROLL.",
        "observation",
        "crater naming",
    ),
    (
        "2026-04-06 22:42:25",
        "We get a blue flash?",
        "observation",
        "Glover at Earthset (unexplained)",
    ),
]

INAUDIBLE = re.compile(r"(?i)\[\[\s*inaudible")
BRACKETED = re.compile(r"\[\[.*?\]\]")


def load(root: Path) -> pl.DataFrame:
    frames = []
    for path in sorted(root.rglob("*_trn-csv_v01.csv")):
        df = pl.read_csv(
            path,
            schema_overrides=dict.fromkeys(("audio_time", "utc", "speaker", "text"), pl.String),
        )
        frames.append(df.with_columns(file=pl.lit(path.name), row=pl.int_range(pl.len())))
    if not frames:
        raise FileNotFoundError(f"no *_trn-csv_v01.csv under {root}")
    return pl.concat(frames).with_columns(
        pl.col("speaker").fill_null(""), pl.col("text").fill_null("")
    )


def quality(df: pl.DataFrame) -> dict:
    ts = df.with_columns(t=pl.col("utc").str.to_datetime("%Y-%m-%d %H:%M:%S%.f", strict=False))
    backwards = ts.with_columns(prev=pl.col("t").shift(1).over("file")).filter(
        pl.col("t") < pl.col("prev")
    )
    malformed = ts.filter(pl.col("t").is_null())["utc"].to_list()
    speakers = Counter(df["speaker"].to_list())
    return {
        "rows": df.height,
        "files": df["file"].n_unique(),
        "blank_speaker_rows": speakers.get("", 0),
        "speakers_with_trailing_space": {s: n for s, n in speakers.items() if s != s.strip()},
        "inaudible_markers": int(df["text"].str.count_matches(INAUDIBLE.pattern).sum()),
        "rows_with_editorial_brackets": int(df["text"].str.contains(BRACKETED.pattern).sum()),
        "timestamps_going_backwards": backwards.height,
        "unparseable_utc": malformed,
    }


def speaker_table(df: pl.DataFrame) -> dict[str, int]:
    base = df.with_columns(s=pl.col("speaker").str.strip_chars().str.replace(r"\s*\[.*$", ""))
    counts = base.group_by("s").len().sort("len", descending=True)
    return {(k or "(blank)"): int(v) for k, v in counts.iter_rows()}


def verify_events(df: pl.DataFrame) -> tuple[list[dict], list[str]]:
    out, missing = [], []
    for utc, frag, cat, label in EVENTS:
        hit = df.filter(
            pl.col("utc").str.starts_with(utc) & pl.col("text").str.contains(frag, literal=True)
        )
        if hit.is_empty():
            missing.append(f"{utc} {frag!r}")
            continue
        row = hit.row(0, named=True)
        out.append({
            "utc": row["utc"], "category": cat, "label": label, "speaker": row["speaker"].strip(),
            "quote": frag, "file": row["file"], "also_in": sorted(set(hit["file"].to_list()) - {row["file"]}),
        })  # fmt: skip
    return out, missing


def per_file(df: pl.DataFrame) -> list[dict]:
    g = (
        df.group_by("file")
        .agg(rows=pl.len(), first=pl.col("utc").min(), last=pl.col("utc").max())
        .sort("file")
    )
    return g.to_dicts()


CUT_S = 60  # an offset jump larger than this means audio was removed from the stitched file
QUIET_MIN = 25  # report conversation gaps at least this long


def _clock_s(col: str) -> pl.Expr:
    parts = pl.col(col).str.split(":")
    return (
        parts.list.get(0).cast(pl.Float64) * 3600
        + parts.list.get(1).cast(pl.Float64) * 60
        + parts.list.get(2).cast(pl.Float64)
    )


def loop_gaps(df: pl.DataFrame) -> dict:
    """Cuts and silences in the voice-loop transcripts.

    `audio_time` is a position in a stitched recording and `utc` is wall-clock time, so
    offset = utc time-of-day - audio_time is constant while the recording runs continuously.
    A jump in the offset means audio was removed between two rows (a cut). A long utc gap
    with an unchanged offset is silence that was kept in the recording.
    """
    loops = (
        df.filter(pl.col("file").str.contains("_oe"))
        .with_columns(t=pl.col("utc").str.to_datetime("%Y-%m-%d %H:%M:%S%.f", strict=False))
        .with_columns(
            offset=(pl.col("t") - pl.col("t").dt.truncate("1d")).dt.total_milliseconds() / 1000
            - _clock_s("audio_time")
        )
    )
    cuts, quiet = [], []
    for name, g in loops.filter(pl.col("t").is_not_null()).group_by("file", maintain_order=True):
        rows = g.sort("row").to_dicts()
        for a, b in pairwise(rows):
            jump = b["offset"] - a["offset"]
            span = (b["t"] - a["t"]).total_seconds() / 60
            rec = {
                "file": name[0],
                "from_utc": a["utc"][:19],
                "to_utc": b["utc"][:19],
                "before": f"{a['speaker'].strip()}: {a['text'].strip()[:90]}",
                "after": f"{b['speaker'].strip()}: {b['text'].strip()[:90]}",
            }
            if abs(jump) > CUT_S:
                cuts.append({**rec, "removed_min": round(jump / 60, 1)})
            elif span >= QUIET_MIN:
                quiet.append({**rec, "silence_kept_min": round(span, 1)})
    undated = loops.filter(pl.col("t").is_null()).select(
        "file", "audio_time", "utc", "speaker", "text"
    )
    return {"cuts": cuts, "silences_kept": quiet, "undated_rows": undated.to_dicts()}


def speakers_in_window(df: pl.DataFrame, start: str, stop: str) -> dict[str, int]:
    """Rows per speaker label in the voice loops between two UTC stamps (inclusive)."""
    win = df.filter(
        pl.col("file").str.contains("_oe") & (pl.col("utc") >= start) & (pl.col("utc") <= stop)
    )
    counts = win.group_by(pl.col("speaker").str.strip_chars()).len().sort("len", descending=True)
    return {k or "(blank)": int(v) for k, v in counts.iter_rows()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", type=Path)
    ap.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parent / "transcript_events.json"
    )
    args = ap.parse_args()

    df = load(args.root)
    events, missing = verify_events(df)
    result = {
        "quality": quality(df),
        "speakers": speaker_table(df),
        "files": per_file(df),
        "events": events,
        "loop_gaps": loop_gaps(df),
        # The President's call: every row is labelled CAPCOM and no crew answer is transcribed.
        "presidential_call_speakers": speakers_in_window(
            df, "2026-04-07 02:25:30", "2026-04-07 02:39:00"
        ),
    }
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result["quality"], indent=1))
    print("events verified:", len(events), "of", len(EVENTS))
    if missing:
        print("NOT FOUND:", *missing, sep="\n  ")
        sys.exit(1)


if __name__ == "__main__":
    main()
