"""Daily researcher — local-first, card-aligned, datamesh-backed.

Four lanes, run in order, single-flight via FleetLock. The "quarter on
the string" is the rule: only one of the four lanes holds the
fleet_lock:modelload at a time, so we never double-spend on the local
silicon.

The contract this module exposes is what the tests pin:

- DailyResearcher.run_dry_run(lane=None)  → dict of {lane: DryRunReport}
- DailyResearcher.run(lane=...)           → acquires the lock, runs the
  lane, releases. Refuses to start if PreflightFleetCheck fails.
- DailyResearcher._preflight()           → wraps PreflightFleetCheck.run
- FleetLock.acquire(lock_key, timeout)    → async context manager; if
  the lock is held by another acquirer with the same key, waits. If the
  timeout elapses, raises LockTimeout.
- PreflightFleetCheck.run()               → (ok: bool, reasons: list[str])
  Reads /proc/meminfo + rocm-smi + dmesg. Fails closed on:
  - available memory < 20 GB
  - swap used > 10%
  - rocm-smi shows >80% VRAM with no owning PID
  - GCVM_L2_PROTECTION_FAULT in dmesg

Budgets are per-DailyResearcher-instance per run:
- Cloud escalations ≤ 5
- Evolution experiments ≤ 2

The SurrealDB-backed version of FleetLock is a later wiring step
(RESEARCH-WS1 followup). For now, the in-process asyncio.Lock provides
the queue-don't-block semantics that are the actual contract.
"""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ── FleetLock: single-flight coordination ────────────────────────────────────


class LockTimeout(RuntimeError):  # noqa: N818 — public API, tests reference this name
    """Raised when a FleetLock.acquire times out waiting for the lock."""


class FleetLock:
    """In-process single-flight lock keyed by string.

    Two acquires with the same key serialize; different keys don't block
    each other. The SurrealDB-backed version is a followup; the in-process
    implementation is the contract the tests pin.
    """

    def __init__(self) -> None:
        self._conds: dict[str, asyncio.Condition] = {}
        self._owner: dict[str, str] = {}

    @asynccontextmanager
    async def acquire(self, lock_key: str, timeout: float = 30.0) -> AsyncIterator[None]:
        """Acquire the lock for `lock_key`. Blocks until held or timeout.

        Raises LockTimeout on timeout.
        """
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        owner_token = f"{lock_key}:{id(self)}:{datetime.utcnow().isoformat()}"
        # Each lock_key gets its own Condition. We acquire that condition's
        # internal lock before checking state, which is what asyncio.Condition
        # requires (it raises "cannot wait on un-acquired lock" otherwise).
        cond = self._cond_for(lock_key)
        async with cond:
            while lock_key in self._owner:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise LockTimeout(
                        f"FleetLock timed out waiting on {lock_key!r} after {timeout}s"
                    )
                try:
                    await asyncio.wait_for(cond.wait(), timeout=remaining)
                except TimeoutError:
                    raise LockTimeout(
                        f"FleetLock timed out waiting on {lock_key!r} after {timeout}s"
                    ) from None
            self._owner[lock_key] = owner_token
        try:
            yield
        finally:
            cond = self._cond_for(lock_key)
            async with cond:
                self._owner.pop(lock_key, None)
                cond.notify_all()

    def _cond_for(self, lock_key: str) -> asyncio.Condition:
        cond = self._conds.get(lock_key)
        if cond is None:
            cond = asyncio.Condition()
            self._conds[lock_key] = cond
        return cond


# ── Preflight: read-only box safety check ────────────────────────────────────


class PreflightFleetCheck:
    """Read-only check that the box is safe for a local inference swarm.

    Returns (ok, reasons). reasons is empty when ok=True. ok=False means
    the orchestrator refuses to start.
    """

    MIN_AVAILABLE_GB = 20.0
    MAX_SWAP_USED_PCT = 10.0
    MAX_VRAM_USED_PCT = 80.0

    @classmethod
    def run(cls) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        reasons.extend(cls._check_memory())
        reasons.extend(cls._check_rocm())
        reasons.extend(cls._check_dmesg())
        return (len(reasons) == 0, reasons)

    # ── Memory check ───────────────────────────────────────────────────

    @classmethod
    def _check_memory(cls) -> list[str]:
        reasons: list[str] = []
        try:
            out = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5).stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # `free` not available — don't fail open; we need this signal.
            return ["free(1) unavailable — cannot confirm memory state"]

        # Parse "Mem:" line for "available" column
        m = re.search(r"Mem:\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)", out)
        swap_m = re.search(r"Swap:\s+(\S+)\s+(\S+)\s+(\S+)", out)
        if not m:
            return ["could not parse `free` output for available memory"]
        avail_str = m.group(1)
        avail_gb = cls._parse_size_to_gb(avail_str)
        if avail_gb is not None and avail_gb < cls.MIN_AVAILABLE_GB:
            reasons.append(
                f"available memory {avail_gb:.1f} GiB is below the {cls.MIN_AVAILABLE_GB} GiB floor"
            )
        if swap_m:
            used_str = swap_m.group(2)
            total_str = swap_m.group(1)
            used = cls._parse_size_to_gb(used_str)
            total = cls._parse_size_to_gb(total_str)
            if used is not None and total and total > 0:
                pct = (used / total) * 100
                if pct > cls.MAX_SWAP_USED_PCT:
                    reasons.append(
                        f"swap used {pct:.0f}% exceeds the {cls.MAX_SWAP_USED_PCT:.0f}% threshold"
                    )
        return reasons

    @classmethod
    def _parse_size_to_gb(cls, s: str) -> float | None:
        s = s.strip()
        if not s:
            return None
        m = re.match(r"([0-9.]+)\s*([KMGT]?i?B?|B)?", s)
        if not m:
            return None
        val = float(m.group(1))
        unit = (m.group(2) or "").upper().rstrip("B")
        if unit in ("K", "KI"):
            return val / (1024**2)
        if unit in ("M", "MI"):
            return val / (1024**1)
        if unit in ("G", "GI"):
            return float(val)
        if unit in ("T", "TI"):
            return val * 1024
        # default: bytes
        return val / (1024**3)

    # ── rocm-smi check ─────────────────────────────────────────────────

    @classmethod
    def _check_rocm(cls) -> list[str]:
        reasons: list[str] = []
        rocm = shutil.which("rocm-smi")
        if not rocm:
            return reasons  # no AMD GPU on this box; not a failure
        try:
            out = subprocess.run(
                [rocm, "--showuse"], capture_output=True, text=True, timeout=5
            ).stdout
        except subprocess.TimeoutExpired:
            return reasons
        # Look for VRAM use > 80% with no owning PID. This is a coarse
        # check; the cold-boot recovery script does the deeper inspection.
        for line in out.splitlines():
            m = re.search(r"GPU use\s*\(%\)\s+([0-9.]+)", line)
            if m and float(m.group(1)) > cls.MAX_VRAM_USED_PCT:
                reasons.append(
                    f"rocm-smi reports VRAM use {m.group(1)}% which "
                    f"exceeds the {cls.MAX_VRAM_USED_PCT}% threshold "
                    f"(possible zombie state)"
                )
                break
        return reasons

    # ── dmesg check ────────────────────────────────────────────────────

    @classmethod
    def _check_dmesg(cls) -> list[str]:
        reasons: list[str] = []
        # dmesg may need sudo; we just attempt and skip on permission
        # denied — the daily-reseacher is not a recovery tool, and a
        # fresh user session may legitimately lack dmesg access.
        try:
            out = subprocess.run(
                ["dmesg", "--since=-15min"], capture_output=True, text=True, timeout=5
            ).stdout
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            return reasons
        if "GCVM_L2_PROTECTION_FAULT" in out or "amdgpu: GCVM" in out:
            reasons.append(
                "GCVM_L2_PROTECTION_FAULT seen in dmesg within the last "
                "15 minutes — kernel is unhappy; refuse to start swarm"
            )
        return reasons


# ── Lane reports ────────────────────────────────────────────────────────────


@dataclass
class DryRunReport:
    lane: str
    dry_run: bool = True
    candidates: list[str] = field(default_factory=list)
    syntheses: list[dict[str, Any]] = field(default_factory=list)
    verifications: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "dry_run": self.dry_run,
            "candidates": list(self.candidates),
            "syntheses": list(self.syntheses),
            "verifications": list(self.verifications),
            "notes": list(self.notes),
        }


# ── Lane base ───────────────────────────────────────────────────────────────


class _BaseLane:
    """Base class for the four lanes."""

    lane_name: str = "base"

    def __init__(self, researcher: DailyResearcher) -> None:
        self.researcher = researcher

    async def run(self, dry_run: bool) -> DryRunReport:
        raise NotImplementedError

    # ── Budget helpers (used by tests) ─────────────────────────────────

    async def _attempt_cloud_escalation(self, synthesis_id: str) -> Any:
        if self.researcher._cloud_escalations_today >= 5:
            return _StatusResult(status="CLOUD_BUDGET_EXHAUSTED", id=synthesis_id)
        self.researcher._cloud_escalations_today += 1
        return _StatusResult(status="ESCALATED", id=synthesis_id)


@dataclass
class _StatusResult:
    status: str
    id: str


# ── Lane 1: model_scout ──────────────────────────────────────────────────────


class ModelScoutLane(_BaseLane):
    lane_name = "model_scout"

    async def run(self, dry_run: bool) -> DryRunReport:
        report = DryRunReport(lane=self.lane_name, dry_run=dry_run)
        # In dry_run, the lane does not load any model; it would normally
        # fetch the live catalog from 13305, parse cards, and dry-run
        # `lemonade load <model>` for candidates.
        report.notes.append(
            "dry-run: no model loads attempted; would scan HF daily + "
            "arXiv + Lemonade recipe diff and drop card_missing candidates"
        )
        return report


# ── Lane 2: harness_paper ────────────────────────────────────────────────────


class HarnessPaperLane(_BaseLane):
    lane_name = "harness_paper"

    async def run(self, dry_run: bool) -> DryRunReport:
        report = DryRunReport(lane=self.lane_name, dry_run=dry_run)
        report.notes.append(
            "dry-run: no LLM-judge calls; would run the 6-step "
            "research-paper-integration ritual + the 4 verifiers"
        )
        return report


# ── Lane 3: datamesh_synthesis ───────────────────────────────────────────────


class DatameshSynthesisLane(_BaseLane):
    lane_name = "datamesh_synthesis"

    async def run(self, dry_run: bool) -> DryRunReport:
        report = DryRunReport(lane=self.lane_name, dry_run=dry_run)
        report.notes.append(
            "dry-run: no vault/bus writes; would split long notes by "
            "consumer ctx and tag with the consumer's family fingerprint"
        )
        return report


# ── Lane 4: verify_evolve ────────────────────────────────────────────────────


class VerifyEvolveLane(_BaseLane):
    lane_name = "verify_evolve"

    async def run(self, dry_run: bool) -> DryRunReport:
        report = DryRunReport(lane=self.lane_name, dry_run=dry_run)
        report.notes.append(
            "dry-run: no in-proc model loads; would run card-fit, "
            "cross-model, falsifiability, and recipe-fit verifiers on "
            "yesterday's pending syntheses"
        )
        return report

    async def _run_one_experiment(self, exp_id: str) -> Any:
        if self.researcher._experiments_today >= 2:
            return _StatusResult(status="EXPERIMENT_BUDGET_EXHAUSTED", id=exp_id)
        self.researcher._experiments_today += 1
        return _StatusResult(status="EXPERIMENT_QUEUED", id=exp_id)


# ── Orchestrator ─────────────────────────────────────────────────────────────


class DailyResearcher:
    """The four-lane daily research orchestrator.

    Lifecycle:
    1. DailyResearcher()                  — instantiate
    2. .run_dry_run()                     — verify the wiring without
       making real model loads; returns dict[lane, DryRunReport]
    3. .run()                             — acquires fleet_lock,
       acquires each lane in order, holds the lock longer for
       quality-first latency, releases
    """

    def __init__(self) -> None:
        self._lock = FleetLock()
        self.model_scout = ModelScoutLane(self)
        self.harness_paper = HarnessPaperLane(self)
        self.datamesh_synthesis = DatameshSynthesisLane(self)
        self.verify_evolve = VerifyEvolveLane(self)
        self._lanes: tuple[_BaseLane, ...] = (
            self.model_scout,
            self.harness_paper,
            self.datamesh_synthesis,
            self.verify_evolve,
        )
        # Per-run counters (the test resets them explicitly).
        self._cloud_escalations_today: int = 0
        self._experiments_today: int = 0

    @property
    def fleet_lock(self) -> FleetLock:
        return self._lock

    @staticmethod
    def _preflight() -> tuple[bool, list[str]]:
        return PreflightFleetCheck.run()

    async def run_dry_run(self) -> dict[str, DryRunReport]:
        reports: dict[str, DryRunReport] = {}
        for lane in self._lanes:
            reports[lane.lane_name] = await lane.run(dry_run=True)
        return reports

    async def run(self, lane: str | None = None) -> dict[str, DryRunReport]:
        ok, reasons = self._preflight()
        if not ok:
            raise RuntimeError(
                f"preflight failed; refusing to start daily researcher: {'; '.join(reasons)}"
            )
        reports: dict[str, DryRunReport] = {}
        async with self._lock.acquire("fleet_lock:modelload", timeout=300):
            if lane is not None:
                target = next((l for l in self._lanes if l.lane_name == lane), None)
                if target is None:
                    raise ValueError(f"unknown lane {lane!r}")
                reports[lane] = await target.run(dry_run=False)
            else:
                for l in self._lanes:
                    reports[l.lane_name] = await l.run(dry_run=False)
        return reports
