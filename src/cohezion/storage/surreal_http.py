"""The one honest way to read a SurrealDB ``/sql`` HTTP response.

SurrealDB answers **HTTP 200** even when every statement failed; the failure is per statement,
as ``{"status": "ERR", "result": "<message>"}`` inside the JSON list. A client that only calls
``raise_for_status()`` (or nothing) and returns ``resp.json()`` therefore reports success for
writes that never happened. Measured 2026-09-19: the vault MCP's ``track_session`` had returned
success ids for rows that never existed since it shipped (wrong header names -> every statement
ERR -> ``len(result) > 0`` == "success"); ``journey_transition`` carried 21,635 rows with a field
the CREATE never included. The same evening a sweep found **67** raw ``/sql`` writers in
``src/cohezion`` with no per-statement check and 8 files that each hand-rolled their own.

This module is the single checker. Every raw HTTP call to ``/sql`` must pass its parsed body
through :func:`checked_statements`; ``scripts/ci/surreal_http_scan.py`` fails CI otherwise.
Stdlib only: reflex-lineage (importable in a fresh interpreter in <100 ms with no cohezion
package), so the sandbox child, hooks and CI probes can use it.
"""

from __future__ import annotations

from typing import Any


__all__ = ["SURREAL_HEADERS", "SurrealQLError", "checked_statements"]

# SurrealDB 2.x reads these; the legacy ``NS``/``DB`` names are silently ignored and yield
# ERR "Specify a namespace to use" on every statement (the exact 2026-09-19 vault-MCP defect).
SURREAL_HEADERS: dict[str, str] = {
    "Content-Type": "text/plain",
    "Accept": "application/json",
}


class SurrealQLError(RuntimeError):
    """A ``/sql`` request that did not do what it was asked.

    Raised for an HTTP error status (with the body, which carries the SurrealQL message that
    ``raise_for_status()`` discards) and for an HTTP 200 whose statement list contains any
    ``status: "ERR"`` entry.
    """

    def __init__(
        self, message: str, *, status_code: int | None = None, failed: list[Any] | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.failed = failed or []


def checked_statements(
    body: Any, *, status_code: int = 200, text: str = "", allow_partial: bool = False
) -> list[dict[str, Any]]:
    """Validate a parsed ``/sql`` response; return the statement list or raise.

    ``body`` is the JSON-decoded response (a list of ``{"status", "result", "time"}`` objects).
    ``status_code``/``text`` let HTTP-level failures surface with their message. With
    ``allow_partial=False`` (the default) ANY ``ERR`` statement raises, because a multi-statement
    write that half-succeeded is a corrupt write. ``allow_partial=True`` returns the list and
    leaves the caller to inspect ``status`` per statement — for read-only probes only.
    """
    if status_code >= 400:
        raise SurrealQLError(f"HTTP {status_code}: {text[:500]}", status_code=status_code)
    if not isinstance(body, list):
        raise SurrealQLError(f"unexpected /sql response shape: {type(body).__name__}")
    failed = [s for s in body if isinstance(s, dict) and s.get("status") == "ERR"]
    if failed and not allow_partial:
        raise SurrealQLError(
            "; ".join(str(s.get("result"))[:300] for s in failed),
            status_code=status_code,
            failed=failed,
        )
    return body
