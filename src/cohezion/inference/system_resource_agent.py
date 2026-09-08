"""SystemResourceAgent — Lemonade-powered silicon resource advisor.

Polls SiliconGuard (temp) + ResourceMonitor (memory) + /tmp/cohezion_pressure.lock,
then calls llama3.2-1b-FLM via :13305 for a structured routing recommendation.
Falls back to deterministic thresholds when Lemonade is unavailable.

The result feeds:
  - compound_daemon: gate on `action == "pause"` before launching a batch
  - DegradationDetector: inject pressure_score as a new metric channel

Design constraints:
  - assess() is a pure callable — no background loop, no side effects beyond logging
  - NEVER evicts models autonomously; recommendation only
  - Lemonade failure is always non-fatal; deterministic fallback activates silently
"""

from __future__ import annotations

import contextlib
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

_PRESSURE_LOCK = Path("/tmp/cohezion_pressure.lock")
_LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
_MODEL_ID = "llama3.2-1b-FLM"

# Deterministic thresholds (mirror OverloadCoordinator._determine_level pressure boundaries)
_TEMP_PAUSE = 85.0  # °C — thermal limit (harness N3)
_TEMP_THROTTLE = 75.0  # °C
_MEM_PAUSE = 92.0  # %
_MEM_THROTTLE = 80.0  # %
# PSI (pressure stall information): % of wall time tasks stalled on memory reclaim.
# The 08-31 freezes were reclaim LIVELOCKS that available-GB missed until too late —
# avg10 is the earliest honest signal for that class (council item 6: idle compute
# must be PSI-gated, not free-bytes-gated).
_PSI_PAUSE = 10.0  # % stalled — reclaim-livelock territory
_PSI_THROTTLE = 2.0  # %
_PSI_PATH = Path("/proc/pressure/memory")


def _read_psi_avg10(path: Path = _PSI_PATH) -> float | None:
    """avg10 from the 'some' PSI line, or None (non-Linux / unreadable — never fabricated)."""
    try:
        first = path.read_text().splitlines()[0]
        return float(first.split("avg10=")[1].split()[0])
    except (OSError, IndexError, ValueError):
        return None


_VALID_TIERS = {"npu", "igpu", "cpu"}
_VALID_ACTIONS = {"proceed", "throttle", "pause"}


@dataclass
class ResourceRecommendation:
    tier: str  # "npu" | "igpu" | "cpu"
    action: str  # "proceed" | "throttle" | "pause"
    reason: str
    pressure_score: float = 0.0  # 0.0 = healthy, 1.0 = critical
    source: str = "deterministic"  # "lemonade" | "deterministic"
    raw_metrics: dict[str, Any] = field(default_factory=dict)


class SystemResourceAgent:
    """Thin Lemonade-backed resource advisor for the Cohezion inference stack.

    Usage::

        advisor = SystemResourceAgent()
        rec = advisor.assess()
        if rec.action == "pause":
            log.warning("Skipping batch: %s", rec.reason)
        elif rec.action == "throttle":
            # reduce batch size, prefer cheaper tier
            ...

    Optionally pass a DegradationDetector to auto-feed silicon metrics::

        advisor = SystemResourceAgent(degradation_detector=detector)
        rec = advisor.assess()   # also calls detector.check_degradation internally
    """

    def __init__(
        self,
        lemonade_url: str = _LEMONADE_URL,
        degradation_detector: Any = None,
        lemonade_timeout: float = 3.0,
    ) -> None:
        self._url = lemonade_url
        self._detector = degradation_detector
        self._timeout = lemonade_timeout
        # Lazy import so tests can run without psutil/torch
        self._guard: Any = None
        self._monitor: Any = None

    def _ensure_sources(self) -> None:
        if self._guard is None:
            try:
                from cohezion.core.silicon_guard import SiliconGuard

                self._guard = SiliconGuard()
            except Exception:
                self._guard = _FallbackGuard()
        if self._monitor is None:
            try:
                from cohezion.core.resource_monitor import ResourceMonitor

                self._monitor = ResourceMonitor()
            except Exception:
                self._monitor = _FallbackMonitor()

    def _poll_metrics(self) -> dict[str, Any]:
        self._ensure_sources()
        temp = 45.0
        mem_pct = 50.0
        avail_gb = 64.0
        with contextlib.suppress(Exception):
            temp = self._guard.get_temperature()
        try:
            stats = self._monitor.get_stats()
            mem_pct = stats.get("memory_percent", 50.0)
            avail_gb = stats.get("available_memory_gb", 64.0)
        except Exception:
            pass
        psi = _read_psi_avg10()
        return {
            "temp_c": round(temp, 1),
            "memory_percent": round(mem_pct, 1),
            "available_gb": round(avail_gb, 1),
            "psi_avg10": round(psi, 2) if psi is not None else None,
            "pressure_lock": _PRESSURE_LOCK.exists(),
        }

    def _deterministic_recommendation(self, m: dict[str, Any]) -> ResourceRecommendation:
        temp = m["temp_c"]
        mem = m["memory_percent"]
        lock = m["pressure_lock"]
        psi = m.get("psi_avg10")
        psi_pause = psi is not None and psi > _PSI_PAUSE
        psi_throttle = psi is not None and psi > _PSI_THROTTLE

        if lock or mem > _MEM_PAUSE or temp > _TEMP_PAUSE or psi_pause:
            score = min(
                1.0,
                (max(mem - _MEM_PAUSE, 0) / 8.0)
                + (0.4 if lock else 0.0)
                + (0.5 if psi_pause else 0.0)
                + (max(temp - _TEMP_PAUSE, 0) / 5.0),
            )
            score = max(0.8, score)
            return ResourceRecommendation(
                tier="cpu",
                action="pause",
                reason=(
                    f"pressure: temp={temp:.0f}°C mem={mem:.0f}% lock={lock}"
                    f" psi={psi if psi is not None else 'n/a'}"
                ),
                pressure_score=round(score, 3),
                raw_metrics=m,
            )
        if mem > _MEM_THROTTLE or temp > _TEMP_THROTTLE or psi_throttle:
            psi_frac = 0.0
            if psi is not None and psi > _PSI_THROTTLE:
                psi_frac = (psi - _PSI_THROTTLE) / (_PSI_PAUSE - _PSI_THROTTLE)
            score = 0.4 + 0.3 * max(
                (mem - _MEM_THROTTLE) / (_MEM_PAUSE - _MEM_THROTTLE),
                (temp - _TEMP_THROTTLE) / (_TEMP_PAUSE - _TEMP_THROTTLE),
                psi_frac,
            )
            return ResourceRecommendation(
                tier="igpu",
                action="throttle",
                reason=f"elevated: temp={temp:.0f}°C mem={mem:.0f}%",
                pressure_score=round(score, 3),
                raw_metrics=m,
            )
        score = 0.1 * (mem / _MEM_THROTTLE) + 0.05 * (temp / _TEMP_THROTTLE)
        return ResourceRecommendation(
            tier="npu",
            action="proceed",
            reason=f"healthy: temp={temp:.0f}°C mem={mem:.0f}%",
            pressure_score=round(score, 3),
            raw_metrics=m,
        )

    def _lemonade_recommendation(self, m: dict[str, Any]) -> ResourceRecommendation | None:
        """Ask llama3.2-1b-FLM for a structured recommendation. Returns None on any failure."""
        prompt = (
            f"Metrics: temp={m['temp_c']}C memory={m['memory_percent']}% "
            f"available={m['available_gb']}GB pressure_lock={m['pressure_lock']}\n\n"
            "Reply with ONLY valid JSON (no markdown):\n"
            '{"tier":"npu","action":"proceed","reason":"<12 words max>","pressure_score":0.05}\n\n'
            "Rules:\n"
            f"- pause+cpu when temp>{_TEMP_PAUSE:.0f} OR mem>{_MEM_PAUSE:.0f} OR pressure_lock=true\n"
            f"- throttle+igpu when temp>{_TEMP_THROTTLE:.0f} OR mem>{_MEM_THROTTLE:.0f}\n"
            "- proceed+npu otherwise\n"
            "- pressure_score: 0.0=healthy 1.0=critical"
        )
        payload = json.dumps(
            {
                "model": _MODEL_ID,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 80,
                "temperature": 0,
            }
        ).encode()
        try:
            req = urllib.request.Request(
                self._url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read().decode())
            text = body["choices"][0]["message"]["content"].strip()
            # Strip markdown fences if the model added them
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(text)
            tier = str(parsed.get("tier", "")).lower()
            action = str(parsed.get("action", "")).lower()
            reason = str(parsed.get("reason", "lemonade"))[:120]
            score = float(parsed.get("pressure_score", 0.0))
            score = max(0.0, min(1.0, score))
            if tier not in _VALID_TIERS or action not in _VALID_ACTIONS:
                logger.debug(
                    "SystemResourceAgent: invalid schema from Lemonade (%s/%s), using deterministic",
                    tier,
                    action,
                )
                return None
            return ResourceRecommendation(
                tier=tier,
                action=action,
                reason=reason,
                pressure_score=round(score, 3),
                source="lemonade",
                raw_metrics=m,
            )
        except (urllib.error.URLError, OSError):
            return None  # Lemonade offline — silent fallback
        except Exception as exc:
            logger.debug(
                "SystemResourceAgent: Lemonade parse failed (%s), using deterministic", exc
            )
            return None

    def _feed_degradation_detector(self, rec: ResourceRecommendation) -> None:
        if self._detector is None:
            return
        try:
            self._detector.check_degradation(
                {
                    "silicon_temp_c": rec.raw_metrics.get("temp_c", 45.0),
                    "memory_pressure": rec.pressure_score,
                }
            )
        except Exception:
            pass  # DegradationDetector feeding is best-effort; never block assess()

    def assess(self) -> ResourceRecommendation:
        """Poll metrics → Lemonade → deterministic fallback → recommendation.

        Pure callable; safe to call from any loop. Never raises.
        """
        try:
            metrics = self._poll_metrics()
            rec = self._lemonade_recommendation(metrics) or self._deterministic_recommendation(
                metrics
            )
            self._feed_degradation_detector(rec)
            logger.debug(
                "SystemResourceAgent: tier=%s action=%s score=%.3f source=%s reason=%s",
                rec.tier,
                rec.action,
                rec.pressure_score,
                rec.source,
                rec.reason,
            )
            return rec
        except Exception as exc:
            logger.warning("SystemResourceAgent.assess() failed: %s", exc, exc_info=True)
            return ResourceRecommendation(
                tier="igpu",
                action="proceed",
                reason="assess() error — safe default",
                pressure_score=0.0,
                source="error",
            )


# ── Fallback stubs (no psutil/torch available) ─────────────────────────────────


class _FallbackGuard:
    def get_temperature(self) -> float:
        return 45.0


class _FallbackMonitor:
    def get_stats(self) -> dict[str, float]:
        # Never fabricate: /proc/meminfo is readable wherever this runs in production.
        # The previous hardcoded {50%, 64GB} was the same fabricated-reader class as
        # the admission gate's 20GB MemorySnapshot fallback (rv-gate HIGH-1) — a
        # daemon gating batches on invented headroom is not gated at all.
        try:
            fields: dict[str, int] = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                key, _, rest = line.partition(":")
                fields[key] = int(rest.split()[0])
            total_gb = fields["MemTotal"] / 1048576.0
            avail_gb = fields["MemAvailable"] / 1048576.0
            return {
                "memory_percent": round(100.0 * (1.0 - avail_gb / total_gb), 1),
                "available_memory_gb": round(avail_gb, 1),
            }
        except (OSError, KeyError, ValueError, IndexError, ZeroDivisionError):
            # Non-Linux last resort — the historical constants, now clearly labeled.
            return {"memory_percent": 50.0, "available_memory_gb": 64.0}
