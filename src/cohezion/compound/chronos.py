"""Chronos — a unified, resource-aware agent over ALL of the box's scheduled jobs.

The Strix Halo box runs jobs under three independent schedulers that share no view of
each other:

  1. **systemd user timers** (``~/.config/systemd/user/*.timer`` + sibling ``*.service``)
     — vault-backup, guardian, git-maintenance, watchdogs, …
  2. **Hermes** (``~/.hermes/cron/jobs.json``) — autoresearch / TCRAO / forge cycles.
  3. **cohezion** (``compound.cron_manager.CronManager``) — session-scoped health polls.

Chronos is the missing *unification + deconfliction* layer. It is **read-only and
non-destructive** by construction: it DISCOVERS jobs from every source into one
``ChronosJob`` view, and — tied into the event-driven ``memory_pressure`` monitor —
ADVISES which jobs to defer when the box is under memory pressure (research bursts yes,
vault-backup / guardian never). It owns no scheduler and mutates no config; control is a
later, permission-gated increment (see ``docs/IMPROVEMENT_BACKLOG.md``).

Wire-at-creation: Chronos composes the existing ``CronManager`` (it does not replace it)
and consumes ``memory_pressure.PressureLevel`` for its advisory — both existing modules.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from cohezion.platform.memory_pressure import PressureLevel, get_pressure_monitor


logger = logging.getLogger(__name__)

_DEFAULT_SYSTEMD_DIR = Path.home() / ".config" / "systemd" / "user"
_DEFAULT_HERMES_JOBS = Path.home() / ".hermes" / "cron" / "jobs.json"

# Jobs whose names/commands match these are SAFE to defer under memory pressure — they are
# best-effort background compute (research bursts), not load-bearing system maintenance.
_DEFERRABLE_KEYWORDS = (
    "research",
    "autoresearch",
    "tcrao",
    "arpao",
    "forge",
    "burst",
    "experiment",
    "distillation",
    "ksearch",
)
# System-critical jobs — NEVER defer these even if a keyword overlaps. Checked FIRST so an
# unfortunate substring can't reclassify a backup or watchdog as throwaway.
_CRITICAL_KEYWORDS = (
    "backup",
    "guardian",
    "relay",
    "maintenance",
    "watchdog",
    "decay",
    "vault",
    "session",
    "restart",
    "forward",
)

_EXEC_START_RE = re.compile(r"^ExecStart=(.*)$", re.MULTILINE)
_ON_CALENDAR_RE = re.compile(r"^OnCalendar=(.*)$", re.MULTILINE)
_ON_ACTIVE_RE = re.compile(r"^OnUnitActiveSec=(.*)$", re.MULTILINE)


def classify_deferrable(name: str, command: str) -> bool:
    """True iff this job is best-effort background compute that may be held under pressure.

    Critical keywords win over deferrable ones, and an unrecognised job defaults to
    NOT deferrable — Chronos never defers what it doesn't understand.
    """
    haystack = f"{name} {command}".lower()
    if any(k in haystack for k in _CRITICAL_KEYWORDS):
        return False
    return any(k in haystack for k in _DEFERRABLE_KEYWORDS)


@dataclass(frozen=True)
class ChronosJob:
    """One scheduled job, normalised across schedulers (read-only view)."""

    source: str  # "systemd" | "hermes" | "cohezion"
    job_id: str
    name: str
    schedule: str  # OnCalendar value or cron expression
    command: str  # ExecStart / prompt-or-script summary ("" if unknown)
    enabled: bool
    last_status: str | None = None

    @property
    def deferrable(self) -> bool:
        return classify_deferrable(self.name, self.command)


class ChronosRegistry:
    """Discovers + unifies scheduled jobs from all sources and gives deferral advice.

    All discovery is fail-soft per-source: a missing/unreadable source contributes an
    empty list rather than raising, so one broken scheduler never blinds the operator to
    the others. Paths and the systemd enabled-set are injectable for testing.
    """

    def __init__(
        self,
        *,
        systemd_dir: Path | None = None,
        hermes_jobs: Path | None = None,
        enabled_units: set[str] | None = None,
    ) -> None:
        self.systemd_dir = systemd_dir if systemd_dir is not None else _DEFAULT_SYSTEMD_DIR
        self.hermes_jobs = hermes_jobs if hermes_jobs is not None else _DEFAULT_HERMES_JOBS
        # When None, every timer is reported enabled=False unless we can prove otherwise.
        # Production callers pass the result of `systemctl --user list-unit-files --state=enabled`.
        self._enabled_units = enabled_units

    # ── per-source discovery ────────────────────────────────────────────────────────
    def discover_systemd(self) -> list[ChronosJob]:
        if not self.systemd_dir.is_dir():
            return []
        jobs: list[ChronosJob] = []
        for timer in sorted(self.systemd_dir.glob("*.timer")):
            try:
                text = timer.read_text()
            except OSError as exc:
                logger.warning("Chronos: cannot read %s: %s", timer, exc)
                continue
            name = timer.stem
            cal = _ON_CALENDAR_RE.search(text) or _ON_ACTIVE_RE.search(text)
            schedule = cal.group(1).strip() if cal else "unknown"
            # Sibling .service is optional (template/orphan timers have none) → degrade.
            service = timer.with_suffix(".service")
            command = ""
            if service.exists():
                try:
                    m = _EXEC_START_RE.search(service.read_text())
                    command = m.group(1).strip() if m else ""
                except OSError:
                    command = ""
            enabled = (
                f"{name}.timer" in self._enabled_units if self._enabled_units is not None else False
            )
            jobs.append(
                ChronosJob(
                    source="systemd",
                    job_id=f"{name}.timer",
                    name=name,
                    schedule=schedule,
                    command=command,
                    enabled=enabled,
                )
            )
        return jobs

    def discover_hermes(self) -> list[ChronosJob]:
        if not self.hermes_jobs.is_file():
            return []
        try:
            data = json.loads(self.hermes_jobs.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Chronos: cannot parse %s: %s", self.hermes_jobs, exc)
            return []
        jobs: list[ChronosJob] = []
        for raw in data.get("jobs", []):
            sched = raw.get("schedule") or {}
            expr = sched.get("expr") if isinstance(sched, dict) else str(sched)
            prompt = (raw.get("prompt") or raw.get("script") or "").strip()
            command = prompt.splitlines()[0][:120] if prompt else ""
            jobs.append(
                ChronosJob(
                    source="hermes",
                    job_id=str(raw.get("id", raw.get("name", "?"))),
                    name=str(raw.get("name", raw.get("id", "?"))),
                    schedule=str(expr or "unknown"),
                    command=command,
                    enabled=bool(raw.get("enabled", True)),
                    last_status=raw.get("last_status"),
                )
            )
        return jobs

    def discover_cohezion(self, manager: object | None = None) -> list[ChronosJob]:
        """In-process CronManager jobs (session-scoped). Composes, never reinvents."""
        if manager is None:
            return []
        status = getattr(manager, "status", None)
        if not callable(status):
            return []
        try:
            snap = status()
        except Exception as exc:  # fail-soft: a broken manager must not blind discovery
            logger.warning("Chronos: CronManager.status() failed: %s", exc)
            return []
        out: list[ChronosJob] = []
        snap_jobs = snap.get("jobs", []) if isinstance(snap, dict) else []
        for j in snap_jobs:
            if not isinstance(j, dict):
                continue
            out.append(
                ChronosJob(
                    source="cohezion",
                    job_id=str(j.get("id", "?")),
                    name=str(j.get("name", j.get("id", "?"))),
                    schedule=str(j.get("cron", "unknown")),
                    command=str(j.get("description", "")),
                    enabled=True,  # registered == active in the session
                )
            )
        return out

    def discover_all(self, manager: object | None = None) -> list[ChronosJob]:
        return [
            *self.discover_systemd(),
            *self.discover_hermes(),
            *self.discover_cohezion(manager),
        ]

    # ── views ───────────────────────────────────────────────────────────────────────
    def summary(self, manager: object | None = None) -> dict[str, object]:
        jobs = self.discover_all(manager)
        by_source: dict[str, int] = {}
        for j in jobs:
            by_source[j.source] = by_source.get(j.source, 0) + 1
        return {
            "total": len(jobs),
            "enabled": sum(1 for j in jobs if j.enabled),
            "deferrable": sum(1 for j in jobs if j.deferrable),
            "by_source": by_source,
        }

    def resource_advisory(
        self,
        *,
        level: PressureLevel | None = None,
        manager: object | None = None,
    ) -> list[ChronosJob]:
        """Jobs Chronos advises DEFERRING right now (report-only — it does not act).

        Only enabled + deferrable jobs, and only when pressure is CRITICAL. At OK/WARNING
        the box has headroom, so nothing is advised. ``level=None`` reads the live
        ``memory_pressure`` monitor's current level.
        """
        if level is None:
            level = get_pressure_monitor().current_level
        if level < PressureLevel.CRITICAL:
            return []
        return [j for j in self.discover_all(manager) if j.enabled and j.deferrable]


_registry: ChronosRegistry | None = None


def get_chronos() -> ChronosRegistry:
    """Process-wide singleton so all callers share one job view."""
    global _registry
    if _registry is None:
        _registry = ChronosRegistry()
    return _registry
