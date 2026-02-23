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
        jsonl_files = sorted(projects_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if jsonl_files:
            return jsonl_files[0]

    # Strategy 2: global most-recent JSONL across all projects
    all_jsonl = sorted(claude_projects.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return all_jsonl[0] if all_jsonl else None


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
