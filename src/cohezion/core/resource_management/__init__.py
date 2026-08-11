"""Resource governance for the session/daemon layer.

Exists because `cohezion-resource-guard.service` has an ExecStart pointing at
`cohezion.core.resource_management.session_monitor`, and that module was missing — the unit had
been in an auto-restart loop (~891 MB peak, ~15 s CPU per attempt, every 10 s) on a box with
documented OOM-freeze history.

The capability itself was never missing: `cohezion.compound.oom_guard` already implements the N3
memory rules. Only the entrypoint the unit names was absent. This package is the thin wiring
between the two — a consumer that existed without its producer.
"""

from __future__ import annotations

__all__ = ["session_monitor"]
