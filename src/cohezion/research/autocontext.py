"""
autocontext — context pressure monitor and experiment state compressor.

Integrates with the autoresearch loop to prevent context overflow:
1. monitor() → reads cz context percentage (via subprocess)
2. compress() → summarizes old autoresearch.jsonl entries into compact form
3. archive() → moves entries older than N hours to archive JSONL
4. budget() → returns how many more experiments are safe to run

Usage in autoresearch loop:
    ctx = autocontext.monitor()
    if ctx['pct'] > 0.80:
        autocontext.compress(jsonl_path, keep_recent=100)
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import timeit
from datetime import datetime
from pathlib import Path
from shutil import which
from typing import Any


def monitor() -> dict[str, Any]:
    """Read current context pressure from cz CLI.

    Returns: {'pct': float, 'status': str, 'safe': bool, 'warn': bool, 'critical': bool,
              'monitor_ms': float}
    """
    t0 = timeit.default_timer()
    cz_bin = which("cz") or "cz"
    try:
        result = subprocess.run(
            [cz_bin, "context", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        data = json.loads(result.stdout)
        pct = data.get("percentage", 0.0) / 100.0
        status = data.get("status", "OK")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pct = 0.0
        status = "UNAVAILABLE"
    return {
        "pct": round(pct, 3),
        "status": status,
        "safe": pct < 0.80,
        "warn": pct >= 0.80,
        "critical": pct >= 0.90,
        "monitor_ms": round((timeit.default_timer() - t0) * 1000, 2),
    }


def compress(jsonl_path: Path, keep_recent: int = 200) -> dict[str, Any]:
    """Compress autoresearch.jsonl by summarizing old entries.

    Keeps the last `keep_recent` entries verbatim.
    Older entries are grouped by experiment label and collapsed into one
    aggregate summary row per experiment.

    Returns: {'kept': int, 'compressed': int, 'summaries_emitted': int, 'elapsed_ms': float}
    """
    t0 = timeit.default_timer()
    jsonl_path = Path(jsonl_path)

    if not jsonl_path.exists():
        return {"kept": 0, "compressed": 0, "summaries_emitted": 0, "elapsed_ms": 0.0}

    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    entries: list[dict] = []
    for line in lines:
        line = line.strip()
        if line:
            with contextlib.suppress(json.JSONDecodeError):
                entries.append(json.loads(line))

    total = len(entries)
    if total <= keep_recent:
        return {
            "kept": total,
            "compressed": 0,
            "summaries_emitted": 0,
            "elapsed_ms": round((timeit.default_timer() - t0) * 1000, 2),
        }

    recent = entries[-keep_recent:]
    old = entries[:-keep_recent]

    # Group old entries by label
    by_label: dict[str, list[dict]] = {}
    for entry in old:
        label = entry.get("label", entry.get("experiment", "unknown"))
        by_label.setdefault(label, []).append(entry)

    summaries: list[dict] = []
    for label, group in by_label.items():
        n = len(group)
        keep_frac = sum(1 for e in group if e.get("keep") == "keep") / n if n else 0.0

        deltas: list[float] = []
        for e in group:
            result = e.get("result", {})
            if isinstance(result, dict):
                for key in ("delta", "gain", "coherence_delta"):
                    val = result.get(key)
                    if isinstance(val, (int, float)):
                        deltas.append(float(val))
                        break

        mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
        max_delta = max(deltas) if deltas else 0.0

        timestamps = [e.get("ts", e.get("wall_ts", "")) for e in group]
        timestamps = [ts for ts in timestamps if ts]
        first_ts = timestamps[0] if timestamps else ""
        last_ts = timestamps[-1] if timestamps else ""

        summaries.append(
            {
                "experiment": label,
                "n": n,
                "keep_frac": round(keep_frac, 3),
                "mean_delta": round(mean_delta, 4),
                "max_delta": round(max_delta, 4),
                "first_ts": first_ts,
                "last_ts": last_ts,
                "compressed": True,
            }
        )

    # Write back: summaries first, then verbatim recent entries
    out_lines: list[str] = []
    for s in summaries:
        out_lines.append(json.dumps(s))
    for e in recent:
        out_lines.append(json.dumps(e))

    jsonl_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    return {
        "kept": len(recent),
        "compressed": len(old),
        "summaries_emitted": len(summaries),
        "elapsed_ms": round((timeit.default_timer() - t0) * 1000, 2),
    }


def budget(ctx: dict | None = None) -> dict[str, Any]:
    """Estimate how many more experiments are safe given context pressure.

    Tiers:
      pct < 0.50  → 1000 remaining
      0.50-0.80   → 200  remaining
      0.80-0.90   → 50   remaining
      > 0.90      → 0    remaining

    Returns: {'remaining_experiments': int, 'safe_to_continue': bool, 'pct': float}
    """
    t0 = timeit.default_timer()
    if ctx is None:
        ctx = monitor()

    pct = ctx.get("pct", 0.0)

    if pct < 0.50:
        remaining = 1000
    elif pct < 0.80:
        remaining = 200
    elif pct < 0.90:
        remaining = 50
    else:
        remaining = 0

    return {
        "remaining_experiments": remaining,
        "safe_to_continue": remaining > 0,
        "pct": pct,
        "elapsed_ms": round((timeit.default_timer() - t0) * 1000, 2),
    }


def archive(jsonl_path: Path, max_age_hours: float = 2.0) -> int:
    """Move entries older than max_age_hours to <jsonl_path>.archive.

    Timestamps are parsed from the 'ts' or 'wall_ts' field as naive datetimes
    (matching autorun_2h.py which writes datetime.now().isoformat()).

    Returns: number of entries archived.
    """
    jsonl_path = Path(jsonl_path)
    if not jsonl_path.exists():
        return 0

    lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    entries: list[dict] = []
    for line in lines:
        line = line.strip()
        if line:
            with contextlib.suppress(json.JSONDecodeError):
                entries.append(json.loads(line))

    if not entries:
        return 0

    # Use naive datetime to match autorun_2h.py's datetime.now().isoformat()
    cutoff = datetime.now()
    cutoff_seconds = max_age_hours * 3600.0

    keep_entries: list[dict] = []
    archive_entries: list[dict] = []

    for entry in entries:
        ts_str = entry.get("ts", entry.get("wall_ts", ""))
        try:
            ts = datetime.fromisoformat(ts_str)
            # If tz-aware, strip timezone for comparison with naive cutoff
            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
            age_seconds = (cutoff - ts).total_seconds()
            if age_seconds > cutoff_seconds:
                archive_entries.append(entry)
            else:
                keep_entries.append(entry)
        except (ValueError, TypeError):
            # Unparseable timestamp → keep in main file
            keep_entries.append(entry)

    if not archive_entries:
        return 0

    # Append to archive file
    archive_path = jsonl_path.with_suffix(jsonl_path.suffix + ".archive")
    with archive_path.open("a", encoding="utf-8") as f:
        for entry in archive_entries:
            f.write(json.dumps(entry) + "\n")

    # Write remaining entries back to main file
    if keep_entries:
        jsonl_path.write_text(
            "\n".join(json.dumps(e) for e in keep_entries) + "\n", encoding="utf-8"
        )
    else:
        jsonl_path.write_text("", encoding="utf-8")

    return len(archive_entries)
