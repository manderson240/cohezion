"""EVI-Gated Proactive Self-Healing System.

Monitors system health, detects drift, calculates EVI for healing actions,
and triggers autonomous self-healing when EVI > 0.75.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter


logger = logging.getLogger(__name__)


@dataclass
class HealingAction:
    """Action proposed for self-healing."""

    action_id: str
    component: str
    issue_description: str
    proposed_remediation: str
    quality_gap: float
    issue_severity: float  # 0.0 to 1.0 (task_importance equivalent)
    remediation_cost: float
    evi_score: float
    approved: bool


class EVIHealer:
    """EVI-gated Proactive Self-Healing System."""

    EVI_THRESHOLD: float = 0.75

    def __init__(self, router: Optional[UnifiedHybridRouter] = None) -> None:
        self.router = router or UnifiedHybridRouter()
        self._history: List[HealingAction] = []

    def evaluate_healing_candidate(
        self,
        component: str,
        issue_description: str,
        proposed_remediation: str,
        quality_gap: float,
        issue_severity: float,
        remediation_cost: float = 0.5,
    ) -> HealingAction:
        """Evaluate whether a proposed healing action meets the EVI > 0.75 threshold."""
        evi_score = (quality_gap * issue_severity) / max(remediation_cost, 1e-4)
        approved = evi_score > self.EVI_THRESHOLD

        action_id = f"heal_{component}_{int(time.time())}"
        action = HealingAction(
            action_id=action_id,
            component=component,
            issue_description=issue_description,
            proposed_remediation=proposed_remediation,
            quality_gap=quality_gap,
            issue_severity=issue_severity,
            remediation_cost=remediation_cost,
            evi_score=evi_score,
            approved=approved,
        )

        self._history.append(action)

        if approved:
            logger.info(
                "EVIHealer APPROVED self-healing action %s for %s (EVI=%.2f > 0.75)",
                action_id,
                component,
                evi_score,
            )
            self._notify_healing(action)
        else:
            logger.info(
                "EVIHealer REJECTED self-healing action %s for %s (EVI=%.2f <= 0.75)",
                action_id,
                component,
                evi_score,
            )

        return action

    def _notify_healing(self, action: HealingAction) -> None:
        """Publish healing notification event and persist kanban item if modules available."""
        try:
            from cohezion.core.event_bus import Event, EventBus
            import asyncio
            bus = EventBus()
            ev = Event.agent_complete(
                agent_name="proactive-evi-healer",
                result={
                    "action_id": action.action_id,
                    "component": action.component,
                    "remediation": action.proposed_remediation,
                    "evi": action.evi_score,
                },
                duration_ms=0.0,
            )
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(bus.publish(ev))
                else:
                    asyncio.run(bus.publish(ev))
            except Exception:
                pass
        except Exception as exc:
            logger.debug("EventBus notification non-blocking exception: %s", exc)

        try:
            from cohezion.data_mesh.kanban_bridge import persist_item
            persist_item(
                {
                    "id": action.action_id,
                    "title": f"[EVI Self-Healing] {action.component}: {action.issue_description[:50]}",
                    "status": "in_progress",
                    "priority": "high" if action.issue_severity > 0.7 else "medium",
                    "source": "proactive/evi_healer",
                    "category": "self_healing",
                }
            )
        except Exception as exc:
            logger.debug("Kanban bridge persistence non-blocking exception: %s", exc)

    def evaluate_trajectory_anomaly(self, drift: float, component: str = "swarm_agent") -> HealingAction:
        """Evaluate Poincaré hyperbolic trajectory drift and trigger anomaly quarantine if drift > 1.5."""
        is_anomalous = drift > 1.5
        severity = 0.9 if is_anomalous else 0.2
        quality_gap = min(1.0, drift / 2.0)
        cost = 0.3

        return self.evaluate_healing_candidate(
            component=f"poincare_quarantine_{component}",
            issue_description=f"Hyperbolic geodesic drift d_B = {drift:.4f} exceeds threshold 1.5",
            proposed_remediation="Isolate anomalous execution thread and reset 2048D state vector to HIHO attractor",
            quality_gap=quality_gap,
            issue_severity=severity,
            remediation_cost=cost,
        )

    def get_action_history(self) -> List[HealingAction]:
        """Return history of evaluated healing actions."""
        return list(self._history)
