"""Session lifecycle management for cohezion-engine."""

import os
import re
from pathlib import Path

from cohezion_engine.config import get_config_dir


_SESSION_ID_RE = re.compile(r"[^a-zA-Z0-9_\-]")


def get_session_id() -> str:
    """Return the current session ID from env var or PID-based fallback.

    The session ID is sanitized to prevent path traversal — only alphanumerics,
    hyphens, and underscores are allowed.
    """
    raw = os.environ.get("COHEZION_SESSION_ID") or f"pid-{os.getpid()}"
    return _SESSION_ID_RE.sub("_", raw)


def get_session_dir(base_dir: Path | None = None) -> Path:
    """Return the session directory, creating it if needed."""
    if base_dir is None:
        base_dir = get_config_dir() / "sessions"
    session_dir = base_dir / get_session_id()
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _continuation_path(base_dir: Path | None = None) -> Path:
    return get_session_dir(base_dir) / "continuation.md"


def write_continuation(content: str, base_dir: Path | None = None) -> Path:
    """Write continuation file for session handoff. Returns the file path."""
    path = _continuation_path(base_dir)
    path.write_text(content)
    return path


def read_continuation(base_dir: Path | None = None) -> str | None:
    """Read continuation file content, or None if it doesn't exist."""
    path = _continuation_path(base_dir)
    if path.exists():
        return path.read_text()
    return None


def delete_continuation(base_dir: Path | None = None) -> None:
    """Delete the continuation file if it exists."""
    path = _continuation_path(base_dir)
    path.unlink(missing_ok=True)


def send_clear(plan_path: str | None = None) -> dict:
    """Trigger a Claude Code session continuation.

    Writes a trigger marker and attempts to signal Claude Code via
    the CLAUDE_CODE_SSE_PORT WebSocket. Falls back to writing a trigger
    file if WebSocket injection is unavailable.

    Returns a dict with keys: success, method, message.
    """
    # Write a trigger file for documentation purposes
    session_dir = get_session_dir()
    trigger_file = session_dir / "send_clear.trigger"
    trigger_content = f"plan={plan_path or 'general'}\n"
    trigger_file.write_text(trigger_content)

    fallback_reason = ""
    sse_port = os.environ.get("CLAUDE_CODE_SSE_PORT")
    if sse_port:
        try:
            import json
            import urllib.request

            # Attempt WebSocket-based clear signal (requires websocket-client)
            # Fall back gracefully if not available
            try:
                import websocket  # type: ignore[import]

                ws = websocket.create_connection(f"ws://localhost:{sse_port}", timeout=3)
                msg = json.dumps({"type": "clear", "plan": plan_path})
                ws.send(msg)
                ws.close()
                return {
                    "success": True,
                    "method": "websocket",
                    "message": "Session clear triggered via WebSocket",
                }
            except ImportError:
                pass  # websocket-client not installed, try HTTP
            except (ConnectionRefusedError, TimeoutError, OSError) as ws_err:
                fallback_reason = f"WebSocket failed: {ws_err}"

            # Fallback: HTTP POST to SSE port
            data = json.dumps({"type": "clear"}).encode()
            req = urllib.request.Request(
                f"http://localhost:{sse_port}/clear",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=3) as resp:
                    return {
                        "success": True,
                        "method": "http",
                        "message": f"HTTP response: {resp.status}",
                    }
            except (
                ConnectionRefusedError,
                TimeoutError,
                OSError,
                urllib.error.URLError,
            ) as http_err:
                fallback_reason = f"HTTP failed: {http_err}"
        except (ConnectionRefusedError, TimeoutError, OSError) as outer_err:
            fallback_reason = f"Connection failed: {outer_err}"

    # Final fallback: trigger file only
    result = {
        "success": False,
        "method": "trigger_file",
        "message": f"Trigger file written to {trigger_file}. Run /clear manually to restart session.",
    }
    if fallback_reason:
        result["fallback_reason"] = fallback_reason
    return result
