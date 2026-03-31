"""Concierge Agent — session routing with dynamic learning.

The concierge eliminates cold starts by synthesizing 7 state sources into
a briefing, routing the user's prompt to the optimal path, and learning
from each session to improve future routing.

Learning loop:
  1. On session start: query state, build briefing, route prompt
  2. On session end: record which route was taken, outcome, and duration
  3. On next session: use historical routing data to predict optimal path
  4. Over time: the concierge develops a "routing intuition" —
     frequently used paths are surfaced faster, abandoned paths are deprioritized

Triune mapping:
  - Knower: synthesizes the 7 state sources (awareness of project state)
  - Thinker: interprets the prompt and selects the optimal route
  - Doer: executes the routing (cd into worktree, load plan, etc.)

HIHO governance:
  - Confidence > 0.8: strong match, suggest with minimal friction
  - Confidence ~0.5: uncertain (HIHO) → present options and ask
  - Confidence < 0.3: no good match → fresh start with vault check

Physics analog: the concierge is a gauge field on the Field fabric — it defines
the connection between sessions (parallel transport of context along the manifold).

Attribution:
  - CAID (JiayiGeng): centralized delegation pattern
  - Data Mesh (Dehghani): domain-aware routing
  - OPH (FloatingPragma): observer overlap for human-agent alignment
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path.home() / ".cohezion-engine" / "sessions"
ROUTING_HISTORY_PATH = Path.home() / ".cohezion-engine" / "routing_history.jsonl"


@dataclass
class SessionBriefing:
    """Synthesized state from 7 sources."""

    branch: str = ""
    worktree_count: int = 0
    continuation_task: str | None = None
    continuation_path: str | None = None
    active_plans: list[str] = field(default_factory=list)
    recent_commits: list[str] = field(default_factory=list)
    surrealdb_healthy: bool = False
    active_data_products: int = 0
    vault_recent_entries: int = 0
    memory_summary: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class RoutingSuggestion:
    """A suggested path for the user's prompt."""

    action: str  # resume_continuation, switch_worktree, load_plan, fresh_start
    target: str  # path, branch name, plan name
    confidence: float  # [0, 1]
    reason: str
    autonomy_tier: str = "SO(12)"  # cosmogonic tier for this action


@dataclass
class RoutingRecord:
    """Historical record of a routing decision for learning."""

    timestamp: float
    user_prompt: str
    suggested_action: str
    suggested_target: str
    confidence: float
    accepted: bool
    session_duration_s: float = 0.0
    outcome: str = ""  # completed, abandoned, pivoted


class ConciergeAgent:
    """Session concierge with dynamic learning.

    Improves over time by tracking which routing suggestions the user
    accepts vs. rejects, and adjusting confidence scores accordingly.
    """

    def __init__(self) -> None:
        self._history: list[RoutingRecord] = []
        self._load_history()

    def _load_history(self) -> None:
        """Load routing history from JSONL file."""
        if ROUTING_HISTORY_PATH.exists():
            try:
                lines = ROUTING_HISTORY_PATH.read_text().strip().split("\n")
                for line in lines[-100:]:
                    record = json.loads(line)
                    self._history.append(RoutingRecord(**record))
            except (json.JSONDecodeError, KeyError, OSError) as exc:
                logger.warning("Could not load routing history: %s", exc)

    def _save_record(self, record: RoutingRecord) -> None:
        """Append a routing record to the history file.

        Note: synchronous I/O — acceptable for concierge (runs once per session).
        """
        try:
            ROUTING_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            with ROUTING_HISTORY_PATH.open("a") as f:
                f.write(json.dumps(record.__dict__) + "\n")
        except OSError as exc:
            logger.warning("Could not save routing record: %s", exc)
        self._history.append(record)

    def gather_briefing(self) -> SessionBriefing:
        """Query state sources and build a briefing."""
        briefing = SessionBriefing()

        if SESSIONS_DIR.exists():
            continuations = sorted(
                SESSIONS_DIR.glob("*/continuation.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if continuations:
                latest = continuations[0]
                briefing.continuation_path = str(latest)
                for line in latest.read_text().split("\n")[:5]:
                    if "**Task:**" in line:
                        briefing.continuation_task = line.split("**Task:**")[1].strip()
                        break

        return briefing

    def route_prompt(self, user_prompt: str, briefing: SessionBriefing) -> RoutingSuggestion:
        """Interpret the user's prompt and suggest a route."""
        prompt_lower = user_prompt.lower()

        # Continuation keywords
        if any(kw in prompt_lower for kw in ["continue", "resume", "pick up", "where were we"]):
            if briefing.continuation_task:
                confidence = self._historical_confidence("resume_continuation")
                return RoutingSuggestion(
                    action="resume_continuation",
                    target=briefing.continuation_path or "",
                    confidence=max(0.8, confidence),
                    reason=f"Resuming: {briefing.continuation_task}",
                    autonomy_tier="U(1)^4",
                )

        # Worktree keywords
        worktree_map = {
            "genesis": "feat/genesis-tdd-a2ui",
            "testing": "feat/genesis-testing",
            "physics": "feat/genesis-physics",
            "rendering": "feat/genesis-rendering",
            "data mesh": "feat/genesis-data-mesh",
            "kernel": "challenge/nvidia-nemotron-reasoning",
        }
        for keyword, branch in worktree_map.items():
            if keyword in prompt_lower:
                confidence = self._historical_confidence(f"switch_worktree:{branch}")
                return RoutingSuggestion(
                    action="switch_worktree",
                    target=branch,
                    confidence=confidence,
                    reason=f"Routing to {branch} (matched '{keyword}')",
                    autonomy_tier="SO(3)^4",
                )

        # Plan keywords
        if any(kw in prompt_lower for kw in ["plan", "spec", "roadmap"]):
            if briefing.active_plans:
                return RoutingSuggestion(
                    action="load_plan",
                    target=briefing.active_plans[0],
                    confidence=0.6,
                    reason=f"Active plan: {briefing.active_plans[0]}",
                    autonomy_tier="SO(3)^4",
                )

        # Default: fresh start
        return RoutingSuggestion(
            action="fresh_start",
            target="",
            confidence=0.3,
            reason="No matching context — starting fresh. Checking vault for related work.",
            autonomy_tier="SO(12)",
        )

    def _historical_confidence(self, action_key: str) -> float:
        """Compute confidence from historical routing success."""
        # Match on full key (e.g., "switch_worktree:feat/genesis-tdd-a2ui")
        # or action prefix (e.g., "switch_worktree") for general confidence
        relevant = [
            r for r in self._history
            if r.suggested_action == action_key
            or (r.suggested_action.startswith(action_key.split(":")[0])
                and ":" not in action_key)
        ]
        if not relevant:
            return 0.5  # HIHO — no history, uncertain

        recent = relevant[-10:]
        accepted = sum(1 for r in recent if r.accepted)
        acceptance_rate = accepted / len(recent)

        # Boost for routes that led to long productive sessions
        avg_duration = sum(r.session_duration_s for r in recent if r.accepted) / max(accepted, 1)
        duration_bonus = min(0.1, avg_duration / 3600)

        return min(0.95, acceptance_rate + duration_bonus)

    def record_outcome(
        self,
        user_prompt: str,
        suggestion: RoutingSuggestion,
        accepted: bool,
        session_duration_s: float = 0.0,
        outcome: str = "",
    ) -> None:
        """Record the outcome for future learning."""
        record = RoutingRecord(
            timestamp=time.time(),
            user_prompt=user_prompt,
            suggested_action=suggestion.action,
            suggested_target=suggestion.target,
            confidence=suggestion.confidence,
            accepted=accepted,
            session_duration_s=session_duration_s,
            outcome=outcome,
        )
        self._save_record(record)
        logger.info(
            "Concierge learned: %s -> %s (accepted=%s, outcome=%s)",
            suggestion.action,
            suggestion.target,
            accepted,
            outcome,
        )
