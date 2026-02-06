"""Reward and Recognition System for Cohezion.

Dual-purpose system that:
1. Motivates through XP, badges, and streaks (gamification)
2. Unlocks real capabilities (models, compute, autonomy tiers)

Features retroactive XP calculation for existing contributions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Achievement:
    """A badge or achievement unlocked by an agent/user."""

    badge_id: str
    name: str
    description: str
    rarity: str  # common, rare, epic, legendary
    unlocked_at: datetime
    xp_bonus: int = 0


@dataclass
class RewardEntry:
    """Single reward transaction."""

    id: str
    agent_id: str
    reward_type: str  # xp, badge, streak, unlock
    amount: int
    description: str
    context: dict[str, Any] = field(default_factory=dict)
    awarded_at: datetime = field(default_factory=datetime.now)


class RewardSystem:
    """Centralized reward and recognition system.

    Tracks:
    - XP accumulation
    - Achievement unlocks
    - Daily streaks
    - Capability unlocks (what XP actually unlocks)

    Retroactively calculates XP for existing work in the repository.
    """

    # XP thresholds for capability unlocks
    UNLOCK_TIERS = {
        1000: {
            "name": "Apprentice",
            "capabilities": ["access_phi3_mini", "access_gemma"],
            "parallel_agents": 2,
            "autonomy_tier": 1,
        },
        2500: {
            "name": "Journeyman",
            "capabilities": ["access_deepseek_7b", "access_qwen_coder"],
            "parallel_agents": 5,
            "autonomy_tier": 2,  # Default: Auto-safe, escalate risky
        },
        5000: {
            "name": "Expert",
            "capabilities": ["access_deepseek_70b", "auto_deploy_safe"],
            "parallel_agents": 10,
            "autonomy_tier": 2,
        },
        10000: {
            "name": "Master",
            "capabilities": ["meta_programming", "generate_agents"],
            "parallel_agents": 20,
            "autonomy_tier": 3,  # Can request full autonomy
        },
        25000: {
            "name": "Architect",
            "capabilities": ["modify_constitution", "charter_voting"],
            "parallel_agents": 50,
            "autonomy_tier": 3,
        },
    }

    # Achievement definitions
    ACHIEVEMENTS = {
        "first_task": {
            "name": "First Steps",
            "description": "Complete your first task",
            "rarity": "common",
            "xp": 50,
        },
        "first_delegation": {
            "name": "Collaborator",
            "description": "Delegate a task to another agent",
            "rarity": "common",
            "xp": 100,
        },
        "phi_80": {
            "name": "Quality Craftsman",
            "description": "Achieve phi-score > 0.8 on a task",
            "rarity": "rare",
            "xp": 250,
        },
        "phi_95": {
            "name": "Perfectionist",
            "description": "Achieve phi-score > 0.95 on a task",
            "rarity": "epic",
            "xp": 500,
        },
        "streak_3": {
            "name": "Dedicated",
            "description": "3-day coding streak",
            "rarity": "rare",
            "xp": 150,
        },
        "streak_7": {
            "name": "Committed",
            "description": "7-day coding streak",
            "rarity": "epic",
            "xp": 500,
        },
        "streak_30": {
            "name": "Legendary",
            "description": "30-day coding streak",
            "rarity": "legendary",
            "xp": 2000,
        },
        "pattern_abstracted": {
            "name": "Pattern Master",
            "description": "Abstract a reusable pattern from code",
            "rarity": "epic",
            "xp": 300,
        },
        "knowledge_contribution": {
            "name": "Knowledge Keeper",
            "description": "Add insight to knowledge graph",
            "rarity": "rare",
            "xp": 100,
        },
        "auto_fix_deployed": {
            "name": "Autonomous Healer",
            "description": "Automatically fix and deploy code",
            "rarity": "legendary",
            "xp": 1000,
        },
    }

    def __init__(self, storage_path: Path | str = "data/rewards"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._ledger: list[RewardEntry] = []
        self._achievements: dict[str, list[Achievement]] = {}
        self._streaks: dict[str, dict[str, Any]] = {}

        # Load existing
        self._load_data()

    def _load_data(self) -> None:
        """Load reward data from storage."""
        ledger_file = self.storage_path / "ledger.jsonl"
        if ledger_file.exists():
            with open(ledger_file) as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self._ledger.append(RewardEntry(**data))

        achievements_file = self.storage_path / "achievements.json"
        if achievements_file.exists():
            with open(achievements_file) as f:
                data = json.load(f)
                for agent_id, achievements in data.items():
                    self._achievements[agent_id] = [
                        Achievement(**a) for a in achievements
                    ]

    def _save_ledger(self, entry: RewardEntry) -> None:
        """Append entry to ledger."""
        ledger_file = self.storage_path / "ledger.jsonl"
        with open(ledger_file, "a") as f:
            f.write(
                json.dumps(
                    {
                        "id": entry.id,
                        "agent_id": entry.agent_id,
                        "reward_type": entry.reward_type,
                        "amount": entry.amount,
                        "description": entry.description,
                        "context": entry.context,
                        "awarded_at": entry.awarded_at.isoformat(),
                    }
                )
                + "\n"
            )

    def award_xp(
        self,
        agent_id: str,
        amount: int,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> RewardEntry:
        """Award XP to an agent."""
        entry = RewardEntry(
            id=f"xp_{datetime.now().timestamp()}",
            agent_id=agent_id,
            reward_type="xp",
            amount=amount,
            description=reason,
            context=context or {},
        )

        self._ledger.append(entry)
        self._save_ledger(entry)

        logger.info(f"🏆 XP Awarded: {agent_id} +{amount} XP ({reason})")

        # Check for tier unlock
        total_xp = self.get_total_xp(agent_id)
        self._check_unlocks(agent_id, total_xp)

        return entry

    def unlock_achievement(self, agent_id: str, badge_id: str) -> Achievement | None:
        """Unlock an achievement for an agent."""
        if badge_id not in self.ACHIEVEMENTS:
            logger.warning(f"Unknown achievement: {badge_id}")
            return None

        # Check if already unlocked
        if agent_id in self._achievements:
            existing = [a.badge_id for a in self._achievements[agent_id]]
            if badge_id in existing:
                return None  # Already has it

        achievement_def = self.ACHIEVEMENTS[badge_id]
        achievement = Achievement(
            badge_id=badge_id,
            name=achievement_def["name"],
            description=achievement_def["description"],
            rarity=achievement_def["rarity"],
            unlocked_at=datetime.now(),
            xp_bonus=achievement_def["xp"],
        )

        if agent_id not in self._achievements:
            self._achievements[agent_id] = []
        self._achievements[agent_id].append(achievement)

        # Save achievements
        self._save_achievements()

        # Award XP for achievement
        self.award_xp(
            agent_id=agent_id,
            amount=achievement_def["xp"],
            reason=f"Achievement unlocked: {achievement_def['name']}",
            context={"badge_id": badge_id, "rarity": achievement_def["rarity"]},
        )

        logger.info(
            f"🎖️ Achievement Unlocked: {agent_id} - {achievement_def['name']} ({achievement_def['rarity']})"
        )

        return achievement

    def _save_achievements(self) -> None:
        """Save achievements to disk."""
        achievements_file = self.storage_path / "achievements.json"
        data = {}
        for agent_id, achievements in self._achievements.items():
            data[agent_id] = [
                {
                    "badge_id": a.badge_id,
                    "name": a.name,
                    "description": a.description,
                    "rarity": a.rarity,
                    "unlocked_at": a.unlocked_at.isoformat(),
                    "xp_bonus": a.xp_bonus,
                }
                for a in achievements
            ]
        with open(achievements_file, "w") as f:
            json.dump(data, f, indent=2)

    def update_streak(
        self, agent_id: str, date: datetime | None = None
    ) -> dict[str, Any]:
        """Update daily streak for an agent."""
        date = date or datetime.now()
        today = date.date()

        if agent_id not in self._streaks:
            self._streaks[agent_id] = {
                "current_streak": 0,
                "last_active": None,
                "longest_streak": 0,
            }

        streak = self._streaks[agent_id]
        last_active = streak.get("last_active")

        if last_active:
            last_date = datetime.fromisoformat(last_active).date()
            diff = (today - last_date).days

            if diff == 0:
                # Already active today
                pass
            elif diff == 1:
                # Consecutive day
                streak["current_streak"] += 1
                streak["last_active"] = date.isoformat()

                # Check streak achievements
                if streak["current_streak"] == 3:
                    self.unlock_achievement(agent_id, "streak_3")
                elif streak["current_streak"] == 7:
                    self.unlock_achievement(agent_id, "streak_7")
                elif streak["current_streak"] == 30:
                    self.unlock_achievement(agent_id, "streak_30")

            else:
                # Streak broken
                streak["longest_streak"] = max(
                    streak["longest_streak"], streak["current_streak"]
                )
                streak["current_streak"] = 1
                streak["last_active"] = date.isoformat()
        else:
            # First activity
            streak["current_streak"] = 1
            streak["last_active"] = date.isoformat()

        return streak

    def get_total_xp(self, agent_id: str) -> int:
        """Get total XP for an agent."""
        total = 0
        for entry in self._ledger:
            if entry.agent_id == agent_id and entry.reward_type == "xp":
                total += entry.amount
        return total

    def get_achievements(self, agent_id: str) -> list[Achievement]:
        """Get all achievements for an agent."""
        return self._achievements.get(agent_id, [])

    def get_unlocked_capabilities(self, agent_id: str) -> dict[str, Any]:
        """Get capabilities unlocked by XP tier."""
        total_xp = self.get_total_xp(agent_id)

        # Find highest unlocked tier
        unlocked_tier = None
        for threshold in sorted(self.UNLOCK_TIERS.keys()):
            if total_xp >= threshold:
                unlocked_tier = self.UNLOCK_TIERS[threshold]

        return unlocked_tier or {
            "name": "Novice",
            "capabilities": [],
            "parallel_agents": 1,
            "autonomy_tier": 1,
        }

    def _check_unlocks(self, agent_id: str, total_xp: int) -> None:
        """Check if agent unlocked new capabilities."""
        for threshold, tier in sorted(self.UNLOCK_TIERS.items()):
            # Check if they just crossed threshold
            previous_xp = total_xp - 10  # Approximate recent award
            if previous_xp < threshold <= total_xp:
                logger.info(
                    f"🔓 TIER UNLOCKED: {agent_id} reached {tier['name']} ({threshold} XP)"
                )
                logger.info(f"   New capabilities: {', '.join(tier['capabilities'])}")
                logger.info(f"   Parallel agents: {tier['parallel_agents']}")

    def calculate_retroactive_xp(
        self,
        agent_id: str,
        git_history: list[dict[str, Any]],
        journey_history: list[dict[str, Any]],
    ) -> int:
        """Calculate XP for existing contributions (retroactive).

        Args:
            agent_id: The agent to calculate for
            git_history: List of commits with metadata
            journey_history: List of past journeys

        Returns:
            Total retroactive XP awarded
        """
        total_retroactive = 0

        logger.info(f"📊 Calculating retroactive XP for {agent_id}...")

        # XP for commits
        for commit in git_history:
            files_changed = commit.get("files_changed", 0)
            insertions = commit.get("insertions", 0)

            # Base XP for commit
            xp = 10

            # Bonus for significant changes
            if files_changed > 5:
                xp += 20
            if insertions > 100:
                xp += 15

            total_retroactive += xp

            # Award retroactively
            self.award_xp(
                agent_id=agent_id,
                amount=xp,
                reason=f"Retroactive: Git commit {commit.get('hash', 'unknown')[:8]}",
                context={"retroactive": True, "commit_hash": commit.get("hash")},
            )

        # XP for completed journeys
        for journey in journey_history:
            phi_score = journey.get("phi_score", 0.5)

            # Base XP for completion
            xp = 25

            # Quality bonus
            if phi_score > 0.8:
                xp += 50
                # Unlock achievement retroactively
                self.unlock_achievement(agent_id, "phi_80")
            if phi_score > 0.95:
                xp += 100
                self.unlock_achievement(agent_id, "phi_95")

            total_retroactive += xp

            self.award_xp(
                agent_id=agent_id,
                amount=xp,
                reason=f"Retroactive: Completed journey {journey.get('id', 'unknown')[:8]}",
                context={"retroactive": True, "phi_score": phi_score},
            )

        logger.info(f"✅ Retroactive XP awarded: {total_retroactive} XP")
        logger.info(f"   New total: {self.get_total_xp(agent_id)} XP")

        return total_retroactive

    def get_leaderboard(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top agents by XP."""
        # Aggregate by agent
        agent_xp: dict[str, int] = {}
        for entry in self._ledger:
            if entry.reward_type == "xp":
                agent_xp[entry.agent_id] = (
                    agent_xp.get(entry.agent_id, 0) + entry.amount
                )

        # Sort by XP
        sorted_agents = sorted(agent_xp.items(), key=lambda x: x[1], reverse=True)

        # Build leaderboard
        leaderboard = []
        for rank, (agent_id, xp) in enumerate(sorted_agents[:limit], 1):
            achievements = self.get_achievements(agent_id)
            tier = self.get_unlocked_capabilities(agent_id)

            leaderboard.append(
                {
                    "rank": rank,
                    "agent_id": agent_id,
                    "xp": xp,
                    "tier": tier["name"],
                    "achievements": len(achievements),
                    "rare_achievements": sum(
                        1 for a in achievements if a.rarity in ["epic", "legendary"]
                    ),
                }
            )

        return leaderboard

    def get_status(self, agent_id: str) -> dict[str, Any]:
        """Get complete reward status for an agent."""
        xp = self.get_total_xp(agent_id)
        achievements = self.get_achievements(agent_id)
        tier = self.get_unlocked_capabilities(agent_id)
        streak = self._streaks.get(agent_id, {"current_streak": 0, "longest_streak": 0})

        # Next unlock
        next_unlock = None
        for threshold in sorted(self.UNLOCK_TIERS.keys()):
            if xp < threshold:
                next_unlock = {
                    "threshold": threshold,
                    "name": self.UNLOCK_TIERS[threshold]["name"],
                    "xp_needed": threshold - xp,
                }
                break

        return {
            "agent_id": agent_id,
            "total_xp": xp,
            "tier": tier["name"],
            "capabilities": tier["capabilities"],
            "parallel_agents": tier["parallel_agents"],
            "autonomy_tier": tier["autonomy_tier"],
            "achievements": [
                {"name": a.name, "rarity": a.rarity, "xp": a.xp_bonus}
                for a in achievements
            ],
            "streak": streak,
            "next_unlock": next_unlock,
        }
