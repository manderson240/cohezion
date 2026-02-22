"""Context usage estimation by reading Claude Code session JSONL files."""
import json
import os
from pathlib import Path

DEFAULT_CONTEXT_LIMIT = 200_000


def _find_active_session_jsonl() -> Path | None:
    """Find the most recently modified session JSONL for the current project."""
    cwd = Path(os.getcwd())
    # Claude Code stores conversations at ~/.claude/projects/<slug>/*.jsonl
    # where slug is the cwd path with / replaced by -
    slug = str(cwd).replace("/", "-").lstrip("-")
    projects_dir = Path.home() / ".claude" / "projects" / slug
    if not projects_dir.exists():
        return None
    jsonl_files = sorted(projects_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return jsonl_files[0] if jsonl_files else None


def estimate_context(
    session_jsonl: Path | None = None,
    context_limit: int = DEFAULT_CONTEXT_LIMIT,
    warn_threshold: float = 80.0,
    clear_threshold: float = 90.0,
) -> dict:
    """Estimate current context usage from the session JSONL file.

    Returns a dict with keys: status, percentage, [error].
    Status values: OK, WARNING, CLEAR_NEEDED, UNKNOWN.
    """
    if session_jsonl is None:
        session_jsonl = _find_active_session_jsonl()

    if session_jsonl is None or not session_jsonl.exists():
        return {
            "status": "UNKNOWN",
            "percentage": 0.0,
            "error": f"Session file not found: {session_jsonl}",
        }

    total_tokens = 0
    try:
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
                total_tokens += usage.get("input_tokens", 0)
                total_tokens += usage.get("cache_creation_input_tokens", 0)
                total_tokens += usage.get("cache_read_input_tokens", 0)
    except OSError as e:
        return {
            "status": "UNKNOWN",
            "percentage": 0.0,
            "error": str(e),
        }

    percentage = (total_tokens / context_limit) * 100.0

    if percentage >= clear_threshold:
        status = "CLEAR_NEEDED"
    elif percentage >= warn_threshold:
        status = "WARNING"
    else:
        status = "OK"

    return {"status": status, "percentage": round(percentage, 4)}
