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
_TEMP_PAUSE = 85.0          # °C — thermal limit (harness N3)
_TEMP_THROTTLE = 75.0       # °C
_MEM_PAUSE = 92.0           # %
_MEM_THROTTLE = 80.0        # %

_VALID_TIERS = {"npu", "igpu", "cpu"}
_VALID_ACTIONS = {"proceed", "throttle", "pause"}


@dataclass
class ResourceRecommendation:
    tier: str               # "npu" | "igpu" | "cpu"
    action: str             # "proceed" | "throttle" | "pause"
    reason: str
    pressure_score: float = 0.0    # 0.0 = healthy, 1.0 = critical
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
            except Exception:  # noqa: BLE001
                self._guard = _FallbackGuard()
        if self._monitor is None:
            try:
                from cohezion.core.resource_monitor import ResourceMonitor
                self._monitor = ResourceMonitor()
            except Exception:  # noqa: BLE001
                self._monitor = _FallbackMonitor()

    def _poll_metrics(self) -> dict[str, Any]:
        self._ensure_sources()
        temp = 45.0
        mem_pct = 50.0
        avail_gb = 64.0
        try:
            temp = self._guard.get_temperature()
        except Exception:  # noqa: BLE001
            pass
        try:
            stats = self._monitor.get_stats()
            mem_pct = stats.get("memory_percent", 50.0)
            avail_gb = stats.get("available_memory_gb", 64.0)
        except Exception:  # noqa: BLE001
            pass
        return {
            "temp_c": round(temp, 1),
            "memory_percent": round(mem_pct, 1),
            "available_gb": round(avail_gb, 1),
            "pressure_lock": _PRESSURE_LOCK.exists(),
        }

    def _deterministic_recommendation(self, m: dict[str, Any]) -> ResourceRecommendation:
        temp = m["temp_c"]
        mem = m["memory_percent"]
        lock = m["pressure_lock"]

        if lock or mem > _MEM_PAUSE or temp > _TEMP_PAUSE:
            score = min(1.0, (max(mem - _MEM_PAUSE, 0) / 8.0) + (0.4 if lock else 0.0) + (max(temp - _TEMP_PAUSE, 0) / 5.0))
            score = max(0.8, score)
            return ResourceRecommendation(
                tier="cpu", action="pause",
                reason=f"pressure: temp={temp:.0f}°C mem={mem:.0f}% lock={lock}",
                pressure_score=round(score, 3), raw_metrics=m,
            )
        if mem > _MEM_THROTTLE or temp > _TEMP_THROTTLE:
            score = 0.4 + 0.3 * max((mem - _MEM_THROTTLE) / (_MEM_PAUSE - _MEM_THROTTLE),
                                     (temp - _TEMP_THROTTLE) / (_TEMP_PAUSE - _TEMP_THROTTLE))
            return ResourceRecommendation(
                tier="igpu", action="throttle",
                reason=f"elevated: temp={temp:.0f}°C mem={mem:.0f}%",
                pressure_score=round(score, 3), raw_metrics=m,
            )
        score = 0.1 * (mem / _MEM_THROTTLE) + 0.05 * (temp / _TEMP_THROTTLE)
        return ResourceRecommendation(
            tier="npu", action="proceed",
            reason=f"healthy: temp={temp:.0f}°C mem={mem:.0f}%",
            pressure_score=round(score, 3), raw_metrics=m,
        )

    def _lemonade_recommendation(self, m: dict[str, Any]) -> ResourceRecommendation | None:
        """Ask llama3.2-1b-FLM for a structured recommendation. Returns None on any failure."""
        prompt = (
            f'Metrics: temp={m["temp_c"]}C memory={m["memory_percent"]}% '
            f'available={m["available_gb"]}GB pressure_lock={m["pressure_lock"]}\n\n'
            "Reply with ONLY valid JSON (no markdown):\n"
            '{"tier":"npu","action":"proceed","reason":"<12 words max>","pressure_score":0.05}\n\n'
            "Rules:\n"
            f"- pause+cpu when temp>{_TEMP_PAUSE:.0f} OR mem>{_MEM_PAUSE:.0f} OR pressure_lock=true\n"
            f"- throttle+igpu when temp>{_TEMP_THROTTLE:.0f} OR mem>{_MEM_THROTTLE:.0f}\n"
            "- proceed+npu otherwise\n"
            "- pressure_score: 0.0=healthy 1.0=critical"
        )
        payload = json.dumps({
            "model": _MODEL_ID,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 80,
            "temperature": 0,
        }).encode()
        try:
            req = urllib.request.Request(
                self._url, data=payload,
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
                logger.debug("SystemResourceAgent: invalid schema from Lemonade (%s/%s), using deterministic", tier, action)
                return None
            return ResourceRecommendation(
                tier=tier, action=action, reason=reason,
                pressure_score=round(score, 3), source="lemonade", raw_metrics=m,
            )
        except (urllib.error.URLError, TimeoutError, OSError):
            return None  # Lemonade offline — silent fallback
        except Exception as exc:  # noqa: BLE001
            logger.debug("SystemResourceAgent: Lemonade parse failed (%s), using deterministic", exc)
            return None

    def _feed_degradation_detector(self, rec: ResourceRecommendation) -> None:
        if self._detector is None:
            return
        try:
            self._detector.check_degradation({
                "silicon_temp_c": rec.raw_metrics.get("temp_c", 45.0),
                "memory_pressure": rec.pressure_score,
            })
        except Exception:  # noqa: BLE001
            pass  # DegradationDetector feeding is best-effort; never block assess()

    def assess(self) -> ResourceRecommendation:
        """Poll metrics → Lemonade → deterministic fallback → recommendation.

        Pure callable; safe to call from any loop. Never raises.
        """
        try:
            metrics = self._poll_metrics()
            rec = self._lemonade_recommendation(metrics) or self._deterministic_recommendation(metrics)
            self._feed_degradation_detector(rec)
            logger.debug(
                "SystemResourceAgent: tier=%s action=%s score=%.3f source=%s reason=%s",
                rec.tier, rec.action, rec.pressure_score, rec.source, rec.reason,
            )
            return rec
        except Exception as exc:  # noqa: BLE001
            logger.warning("SystemResourceAgent.assess() failed: %s", exc, exc_info=True)
            return ResourceRecommendation(
                tier="igpu", action="proceed",
                reason="assess() error — safe default",
                pressure_score=0.0, source="error",
            )


# ── Fallback stubs (no psutil/torch available) ─────────────────────────────────

class _FallbackGuard:
    def get_temperature(self) -> float:
        return 45.0


class _FallbackMonitor:
    def get_stats(self) -> dict[str, float]:
        return {"memory_percent": 50.0, "available_memory_gb": 64.0}
