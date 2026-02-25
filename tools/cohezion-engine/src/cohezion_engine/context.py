"""Context usage estimation by reading Claude Code session JSONL files."""

import json
import os
from pathlib import Path

DEFAULT_CONTEXT_LIMIT = 200_000


def _find_active_session_jsonl() -> Path | None:
    """Find the most recently modified session JSONL for the current project.

    Strategy:
    1. Try the cwd-based slug (exact match for the current project).
    2. Fall back to scanning all project dirs and returning the globally most
       recent JSONL.  This handles subprocess/hook contexts where the working
       directory may differ from the directory Claude Code is actually running in.
    """
    claude_projects = Path.home() / ".claude" / "projects"
    if not claude_projects.exists():
        return None

    # Strategy 1: cwd-derived slug
    cwd = Path(os.getcwd())
    slug = str(cwd).replace("/", "-").lstrip("-")
    projects_dir = claude_projects / slug
    if projects_dir.exists():
        jsonl_files = sorted(
            projects_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if jsonl_files:
            return jsonl_files[0]

    # Strategy 2: global most-recent JSONL across all projects
    all_jsonl = sorted(
        claude_projects.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return all_jsonl[0] if all_jsonl else None


def _parse_turns(session_jsonl: Path) -> list[dict]:
    """Parse assistant turns from JSONL, returning per-turn token dicts.

    Each dict has keys: input_tokens, cache_creation, cache_read, output_tokens, total.
    """
    turns = []
    with session_jsonl.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = record.get("message", {})
            if msg.get("role") != "assistant":
                continue
            usage = msg.get("usage", {})
            inp = usage.get("input_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            out = usage.get("output_tokens", 0)
            turns.append(
                {
                    "input_tokens": inp,
                    "cache_creation": cache_create,
                    "cache_read": cache_read,
                    "output_tokens": out,
                    "total": inp + cache_create + cache_read + out,
                }
            )
    return turns


def estimate_context(
    session_jsonl: Path | None = None,
    context_limit: int = DEFAULT_CONTEXT_LIMIT,
    warn_threshold: float = 80.0,
    clear_threshold: float = 90.0,
    velocity_window: int = 5,
    top_turns: int = 0,
    hypothetical_tokens: int = 0,
) -> dict:
    """Estimate current context usage from the session JSONL file.

    Returns a dict with keys: status, percentage, output_tokens,
    velocity_tokens_per_turn, turns_remaining, [top_turns], [error].
    Status values: OK, WARNING, CLEAR_NEEDED, UNKNOWN.

    Args:
        velocity_window: Number of recent turns to average for velocity.
        top_turns: If > 0, include the N most expensive turns in result.
        hypothetical_tokens: If > 0, project status after adding these tokens.
    """
    if session_jsonl is None:
        session_jsonl = _find_active_session_jsonl()

    if session_jsonl is None or not session_jsonl.exists():
        return {
            "status": "UNKNOWN",
            "percentage": 0.0,
            "output_tokens": 0,
            "velocity_tokens_per_turn": 0,
            "turns_remaining": None,
            "error": f"Session file not found: {session_jsonl}",
        }

    try:
        turns = _parse_turns(session_jsonl)
    except OSError as e:
        return {
            "status": "UNKNOWN",
            "percentage": 0.0,
            "output_tokens": 0,
            "velocity_tokens_per_turn": 0,
            "turns_remaining": None,
            "error": str(e),
        }

    if not turns:
        base: dict = {
            "status": "OK",
            "percentage": 0.0,
            "output_tokens": 0,
            "velocity_tokens_per_turn": 0,
            "turns_remaining": None,
        }
        if hypothetical_tokens:
            base.update(
                _hypothetical_fields(
                    0, hypothetical_tokens, context_limit, warn_threshold, clear_threshold
                )
            )
        return base

    # Aggregate totals — preserve existing behaviour: sum input+cache tokens across all turns
    total_input = sum(t["input_tokens"] + t["cache_creation"] + t["cache_read"] for t in turns)
    total_output = sum(t["output_tokens"] for t in turns)
    total_tokens = total_input

    # Velocity: average per-turn cost over the last velocity_window turns
    window = turns[-velocity_window:] if velocity_window > 0 else turns
    velocity = int(sum(t["total"] for t in window) / len(window)) if window else 0

    # Turns remaining based on remaining input capacity and velocity
    remaining = max(0, context_limit - total_tokens)
    turns_remaining: int | None = (remaining // velocity) if velocity > 0 else None

    effective_tokens = total_tokens + hypothetical_tokens
    percentage = (effective_tokens / context_limit) * 100.0

    if percentage >= clear_threshold:
        status = "CLEAR_NEEDED"
    elif percentage >= warn_threshold:
        status = "WARNING"
    else:
        status = "OK"

    result: dict = {
        "status": status,
        "percentage": round(percentage, 4),
        "output_tokens": total_output,
        "velocity_tokens_per_turn": velocity,
        "turns_remaining": turns_remaining,
    }

    if hypothetical_tokens:
        result.update(
            _hypothetical_fields(
                total_tokens, hypothetical_tokens, context_limit, warn_threshold, clear_threshold
            )
        )

    if top_turns > 0:
        ranked = sorted(
            [{"turn": i + 1, "tokens": t["total"]} for i, t in enumerate(turns)],
            key=lambda x: x["tokens"],
            reverse=True,
        )
        result["top_turns"] = ranked[:top_turns]

    return result


def _hypothetical_fields(
    current_tokens: int,
    hypothetical_tokens: int,
    context_limit: int,
    warn_threshold: float,
    clear_threshold: float,
) -> dict:
    """Return fits/status_after/percentage_after for a hypothetical token addition."""
    pct = ((current_tokens + hypothetical_tokens) / context_limit) * 100.0
    if pct >= clear_threshold:
        status = "CLEAR_NEEDED"
    elif pct >= warn_threshold:
        status = "WARNING"
    else:
        status = "OK"
    return {
        "fits": pct < clear_threshold,
        "status_after": status,
        "percentage_after": round(pct, 4),
    }


def write_context_snapshot(session_dir: Path, context_result: dict) -> Path:
    """Write a context snapshot JSON to session_dir/context-snapshots/.

    Returns the path of the written snapshot file.
    """
    import datetime

    snapshots_dir = session_dir / "context-snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    snapshot_path = snapshots_dir / f"{timestamp}.json"
    snapshot_path.write_text(json.dumps({**context_result, "timestamp": timestamp}, indent=2))
    return snapshot_path


def read_previous_status(session_dir: Path) -> str | None:
    """Read the last recorded context status from the session directory."""
    status_file = session_dir / "context-status.txt"
    if status_file.exists():
        return status_file.read_text().strip() or None
    return None


def write_current_status(session_dir: Path, status: str) -> None:
    """Persist the current context status to the session directory."""
    (session_dir / "context-status.txt").write_text(status)
