"""Usage log for tracking inference spend.

JSONL-based: each call to record_usage appends one JSON line.
Record format: {"model": ..., "lane": ..., "input_tokens": ...,
                "output_tokens": ..., "cost_usd": ..., "local": ...}

Used by frontier_oracle.fable_spend_usd to gate Fable spend against a monthly cap.
"""

from __future__ import annotations

import json
from pathlib import Path

_DEFAULT_LOG = Path.home() / ".cohezion" / "usage.jsonl"


def record_usage(
    model: str,
    lane: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    local: bool,
    path: str | Path | None = None,
) -> None:
    """Append a single inference usage record to the JSONL log at *path*."""
    log_path = Path(path) if path else _DEFAULT_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "model": model,
        "lane": lane,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "local": local,
    }
    with log_path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def read_usage_log(path: str | Path | None = None) -> list[dict]:
    """Return all usage records from the JSONL log at *path* as dicts."""
    log_path = Path(path) if path else _DEFAULT_LOG
    if not log_path.exists():
        return []
    records: list[dict] = []
    try:
        with log_path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        pass
    return records
