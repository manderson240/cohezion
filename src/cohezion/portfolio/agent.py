"""Cohezion Portfolio Agent — local-inference-powered project status updater.

Uses the Triune Orchestrator (NPU :13306 → iGPU :13307 → CPU :13309) to parse
unstructured session notes into structured portfolio updates.  Falls back to
a simple regex heuristic when local inference is offline.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from cohezion.portfolio.models import PortfolioProject
from cohezion.portfolio.tracker import PortfolioTracker, get_tracker


logger = logging.getLogger(__name__)


class PortfolioAgent:
    """Analyses session text and updates portfolio project status.

    Usage::

        agent = PortfolioAgent()
        agent.process_session_note(
            project_id="nemotron",
            session_id="abc123",
            text="Kernel finished. Score 0.85 on public LB. Submitted v10.",
        )
    """

    def __init__(self, tracker: PortfolioTracker | None = None) -> None:
        self._tracker = tracker or get_tracker()
        self._orchestrator: Any = None
        self._provider_available = False
        self._try_init_orchestrator()

    def _try_init_orchestrator(self) -> None:
        """Lazy-init the local inference provider; silently skip if offline."""
        try:
            from cohezion.compound.local_inference import lemonade_available
            from cohezion.inference.triune_orchestrator import build_triune_orchestrator

            if lemonade_available():
                self._orchestrator = build_triune_orchestrator()
                self._provider_available = True
                logger.info("PortfolioAgent: Triune orchestrator online")
            else:
                logger.info("PortfolioAgent: local inference offline, using heuristics")
        except ImportError:
            logger.debug("PortfolioAgent: inference modules unavailable")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_session_note(
        self,
        project_id: str,
        session_id: str,
        text: str,
    ) -> PortfolioProject | None:
        """Parse `text` and update the tracked project."""
        project = self._tracker.get(project_id)
        if project is None:
            logger.warning("project %s not found in tracker", project_id)
            return None

        if self._provider_available and self._orchestrator is not None:
            updates = self._llm_extract(text)
        else:
            updates = self._heuristic_extract(text)

        return self._tracker.update_from_session(
            project_id,
            session_id=session_id,
            note=text[:200],
            **updates,
        )

    def bulk_status_report(self) -> str:
        """Generate a markdown status report for all tracked projects."""
        summaries = self._tracker.summaries()
        lines = ["# Cohezion Portfolio Status\n"]
        for s in summaries:
            urgency = " ⚠️" if s.is_urgent else ""
            deadline_str = s.deadline.strftime("%b %d") if s.deadline else "—"
            prize_str = f"${s.prize:,}" if s.prize else "non-cash"
            score_str = s.score_label or "—"
            days_str = f"{s.days_to_deadline}d" if s.days_to_deadline is not None else "—"
            lines.append(
                f"| **{s.name}**{urgency} | {s.status.upper()} | {score_str} | "
                f"{deadline_str} ({days_str}) | {prize_str} |"
            )
        header = "| Project | Status | Score | Deadline | Prize |\n|---|---|---|---|---|"
        return lines[0] + header + "\n" + "\n".join(lines[1:])

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _heuristic_extract(self, text: str) -> dict[str, Any]:
        """Simple regex-based extraction when LLM is offline."""
        updates: dict[str, Any] = {}

        # Score detection: "0.84", "score 0.85", "187.4 pts"
        score_m = re.search(r"\bscore[d]?\s+([\d.]+)", text, re.I)
        if not score_m:
            score_m = re.search(r"\b(0\.\d{2,4})\s*(on|public|private|lb)", text, re.I)
        if score_m:
            try:
                updates["score"] = float(score_m.group(1))
                updates["score_label"] = f"{score_m.group(1)} public"
            except ValueError:
                pass

        # Status keywords
        text_lower = text.lower()
        if any(w in text_lower for w in ("submitted", "submission")):
            updates["status"] = "submitted"
        elif any(w in text_lower for w in ("complete", "finished", "done")):
            updates["status"] = "complete"
        elif any(w in text_lower for w in ("running", "training", "in progress")):
            updates["status"] = "running"

        # Kernel slug: manderson240/something
        kernel_m = re.search(r"manderson240/([\w-]+)", text)
        if kernel_m:
            updates["kernel"] = f"manderson240/{kernel_m.group(1)}"

        return updates

    def _llm_extract(self, text: str) -> dict[str, Any]:
        """Use local inference to extract structured updates from session note."""
        try:
            import json as _json

            prompt = (
                "Extract portfolio update from this session note. "
                "Reply ONLY with a JSON object containing any of these keys "
                "(omit keys you cannot determine): "
                "status (one of: active running complete submitted banked deferred), "
                "score (float), score_label (string), kernel (string kaggle slug). "
                f"\n\nNote: {text[:500]}"
            )
            # Triune orchestrator: returns a response object or string
            response = self._orchestrator.route_and_execute(prompt)
            result_text = response if isinstance(response, str) else str(response)
            # Extract JSON from response
            m = re.search(r"\{[^}]+\}", result_text, re.S)
            if m:
                return _json.loads(m.group(0))
        except Exception as exc:
            logger.debug("LLM extraction failed, falling back to heuristics: %s", exc)

        return self._heuristic_extract(text)
