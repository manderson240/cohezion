"""Reward System — tracks XP, achievements, and agent progression.

Provides gamification mechanics for agent performance tracking:
- XP accumulation based on task quality (phi scores)
- Achievement unlocking for milestones
- Streak tracking for consistent performance
- Tier-based capability unlocking
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


class RewardSystem:
    """Track and manage agent rewards, achievements, and progression.

    This is a minimal implementation that stores state in-memory.
    A future version will persist to SurrealDB.
    """

    def __init__(self) -> None:
        self._agents: dict[str, dict[str, Any]] = {}

    def _ensure_agent(self, agent_id: str) -> dict[str, Any]:
        """Get or create agent reward state."""
        if agent_id not in self._agents:
            self._agents[agent_id] = {
                "total_xp": 0,
                "tier": "Novice",
                "achievements": [],
                "streak": {"current": 0, "longest": 0},
            }
        return self._agents[agent_id]

    def award_xp(
        self,
        agent_id: str,
        amount: int,
        reason: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Award XP to an agent.

        Parameters
        ----------
        agent_id : str
            The agent identifier.
        amount : int
            XP amount to award.
        reason : str
            Reason for the award.
        context : dict, optional
            Additional context metadata.
        """
        state = self._ensure_agent(agent_id)
        state["total_xp"] += amount
        logger.debug("Awarded %d XP to %s: %s", amount, agent_id, reason)

    def unlock_achievement(self, agent_id: str, badge_id: str) -> None:
        """Unlock an achievement badge for an agent.

        Parameters
        ----------
        agent_id : str
            The agent identifier.
        badge_id : str
            The achievement badge to unlock.
        """
        state = self._ensure_agent(agent_id)
        if badge_id not in state["achievements"]:
            state["achievements"].append(badge_id)
            logger.debug("Achievement unlocked for %s: %s", agent_id, badge_id)

    def get_status(self, agent_id: str) -> dict[str, Any]:
        """Get the reward status for an agent.

        Parameters
        ----------
        agent_id : str
            The agent identifier.

        Returns
        -------
        dict[str, Any]
            Agent reward state including XP, tier, achievements, streak.
        """
        return self._ensure_agent(agent_id)
