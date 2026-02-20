"""Git-safe persistence and handoff mechanisms."""

from __future__ import annotations

from .session_manager import SessionManager, SessionSnapshot

__all__ = ["SessionManager", "SessionSnapshot"]
