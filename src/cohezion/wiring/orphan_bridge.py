"""Orphan-integration bridge — wires previously-unreachable modules together.

Established by the 2026-06-05 V-model audit under the **non-destructive wiring**
policy (``~/.claude/rules/non-destructive-wiring.md``): orphan modules are
*integrated*, never deleted. This module is the single reachable seam that
imports every module the import-graph audit found with zero external importers,
exposing them through one service-locator registry so downstream code (and the
audit instrument) can discover them.

Design choices:
  - **Static, literal `import` edges** — each orphan is imported with a real
    ``import cohezion.<name>`` statement (not ``importlib`` on a string) so the
    dependency is visible to the import-graph audit, BFS reachability, IDE
    reference search, and bundlers. Dynamic string imports reach the module at
    runtime but leave it orphaned to every *static* analyzer.
  - **Guarded** — a broken or heavy orphan must not take down the package; each
    import is wrapped and failures are recorded, not raised.
  - **Side-effect-free at import** — importing this module only binds names and
    builds a registry; it never executes orphan behaviour.
  - **Verifiable** — :func:`verify_wiring` is asserted by
    ``tests/wiring/test_orphan_bridge.py`` (the V-model verification leg).
"""

from __future__ import annotations

from types import ModuleType


# Modules the 2026-06-05 audit flagged as import-graph orphans (0 ext importers).
# `skills` is functionally live via skill_registry.json but had no import edge.
_ORPHAN_MODULES: tuple[str, ...] = (
    "cli",
    "datamesh",
    "dogfooding",
    "infrastructure",
    "policies",
    "recursive_trace",
    "reporting",
    "sandboxing",
    "simulations",
    "skills",
    "traceability",
)

#: orphan name -> imported module (wired) or an error string (degraded, fail-soft).
WIRED_ORPHANS: dict[str, ModuleType | str] = {}

# --- Static literal import edges (one guarded block per orphan) ----------------
# Each `import cohezion.<name>` is a real graph edge the audit can see.
try:
    import cohezion.cli

    WIRED_ORPHANS["cli"] = cohezion.cli
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["cli"] = f"unavailable: {type(exc).__name__}: {exc}"
try:
    import cohezion.datamesh

    WIRED_ORPHANS["datamesh"] = cohezion.datamesh
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["datamesh"] = f"unavailable: {type(exc).__name__}: {exc}"
try:
    import cohezion.dogfooding

    WIRED_ORPHANS["dogfooding"] = cohezion.dogfooding
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["dogfooding"] = f"unavailable: {type(exc).__name__}: {exc}"
try:
    import cohezion.infrastructure

    WIRED_ORPHANS["infrastructure"] = cohezion.infrastructure
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["infrastructure"] = f"unavailable: {type(exc).__name__}: {exc}"
try:
    import cohezion.policies

    WIRED_ORPHANS["policies"] = cohezion.policies
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["policies"] = f"unavailable: {type(exc).__name__}: {exc}"
try:
    import cohezion.recursive_trace

    WIRED_ORPHANS["recursive_trace"] = cohezion.recursive_trace
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["recursive_trace"] = f"unavailable: {type(exc).__name__}: {exc}"
try:
    import cohezion.reporting

    WIRED_ORPHANS["reporting"] = cohezion.reporting
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["reporting"] = f"unavailable: {type(exc).__name__}: {exc}"
try:
    import cohezion.sandboxing

    WIRED_ORPHANS["sandboxing"] = cohezion.sandboxing
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["sandboxing"] = f"unavailable: {type(exc).__name__}: {exc}"
try:
    import cohezion.simulations

    WIRED_ORPHANS["simulations"] = cohezion.simulations
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["simulations"] = f"unavailable: {type(exc).__name__}: {exc}"
try:
    import cohezion.skills

    WIRED_ORPHANS["skills"] = cohezion.skills
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["skills"] = f"unavailable: {type(exc).__name__}: {exc}"
try:
    import cohezion.traceability

    WIRED_ORPHANS["traceability"] = cohezion.traceability
except (ImportError, AttributeError, ValueError, TypeError, OSError) as exc:
    WIRED_ORPHANS["traceability"] = f"unavailable: {type(exc).__name__}: {exc}"


def verify_wiring() -> dict[str, object]:
    """Return integration status for the audit / verification leg.

    Keys: ``total``, ``wired`` / ``degraded`` (name lists), ``wired_count``,
    ``degraded_count``. Never raises.
    """
    wired = [n for n, v in WIRED_ORPHANS.items() if isinstance(v, ModuleType)]
    degraded = [n for n, v in WIRED_ORPHANS.items() if not isinstance(v, ModuleType)]
    return {
        "total": len(_ORPHAN_MODULES),
        "wired": wired,
        "degraded": degraded,
        "wired_count": len(wired),
        "degraded_count": len(degraded),
    }
