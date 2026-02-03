"""Strategy Orchestrator.

Strategic planning and coordination layer that synthesizes
insights into actionable growth initiatives.
"""

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class StrategicGoal:
    """Strategic goal or objective."""

    goal_id: str
    name: str
    description: str
    priority: Priority
    status: str
    created_at: datetime
    target_date: datetime | None
    progress: float
    dependencies: list[str]
    tasks: list[dict]


@dataclass
class StrategicInitiative:
    """Collection of related goals forming an initiative."""

    initiative_id: str
    name: str
    description: str
    goals: list[StrategicGoal]
    expected_impact: float
    status: str


class StrategyOrchestrator:
    """
    Strategic orchestration for autonomous growth.

    Responsibilities:
    - Synthesize insights into strategic goals
    - Prioritize initiatives based on impact
    - Coordinate execution across systems
    - Track progress and adapt strategy
    """

    def __init__(self, storage_path: str = "data/strategy"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.goals: dict[str, StrategicGoal] = {}
        self.initiatives: dict[str, StrategicInitiative] = {}
        self._load_strategy()

    def _load_strategy(self) -> None:
        """Load existing strategy from storage."""
        goals_file = self.storage_path / "goals.json"
        initiatives_file = self.storage_path / "initiatives.json"

        if goals_file.exists():
            with open(goals_file) as f:
                data = json.load(f)
                for g in data:
                    self.goals[g["goal_id"]] = StrategicGoal(
                        goal_id=g["goal_id"],
                        name=g["name"],
                        description=g["description"],
                        priority=Priority(g["priority"]),
                        status=g["status"],
                        created_at=datetime.fromisoformat(g["created_at"]),
                        target_date=datetime.fromisoformat(g["target_date"])
                        if g.get("target_date")
                        else None,
                        progress=g["progress"],
                        dependencies=g.get("dependencies", []),
                        tasks=g.get("tasks", []),
                    )

        if initiatives_file.exists():
            with open(initiatives_file) as f:
                data = json.load(f)
                for i in data:
                    self.initiatives[i["initiative_id"]] = StrategicInitiative(
                        initiative_id=i["initiative_id"],
                        name=i["name"],
                        description=i["description"],
                        goals=[],
                        expected_impact=i["expected_impact"],
                        status=i["status"],
                    )

    def _save_strategy(self) -> None:
        """Persist strategy to storage."""
        goals_file = self.storage_path / "goals.json"
        initiatives_file = self.storage_path / "initiatives.json"

        with open(goals_file, "w") as f:
            json.dump(
                [
                    {
                        "goal_id": g.goal_id,
                        "name": g.name,
                        "description": g.description,
                        "priority": g.priority.value,
                        "status": g.status,
                        "created_at": g.created_at.isoformat(),
                        "target_date": g.target_date.isoformat()
                        if g.target_date
                        else None,
                        "progress": g.progress,
                        "dependencies": g.dependencies,
                        "tasks": g.tasks,
                    }
                    for g in self.goals.values()
                ],
                f,
                indent=2,
                default=str,
            )

        with open(initiatives_file, "w") as f:
            json.dump(
                [
                    {
                        "initiative_id": i.initiative_id,
                        "name": i.name,
                        "description": i.description,
                        "goals": [g.goal_id for g in i.goals],
                        "expected_impact": i.expected_impact,
                        "status": i.status,
                    }
                    for i in self.initiatives.values()
                ],
                f,
                indent=2,
            )

    async def synthesize_goals_from_insights(
        self, insights: list[dict]
    ) -> list[StrategicGoal]:
        """Create strategic goals from synthesis insights."""
        goals = []

        for insight in insights:
            impact = insight.get("impact_score", 0.5)
            ptype = insight.get("pattern_type", "unknown")

            if impact > 0.7:
                priority = Priority.CRITICAL
            elif impact > 0.5:
                priority = Priority.HIGH
            elif impact > 0.3:
                priority = Priority.MEDIUM
            else:
                priority = Priority.LOW

            goal = StrategicGoal(
                goal_id=f"goal_{insight.get('pattern_id', hashlib.md5(str(insight).encode()).hexdigest()[:8])}",
                name=f"Address: {ptype}",
                description=insight.get("description", "No description"),
                priority=priority,
                status="pending",
                created_at=datetime.now(),
                target_date=datetime.now()
                + timedelta(days=7 if priority.value <= 2 else 14),
                progress=0.0,
                dependencies=[],
                tasks=[
                    {"task": r, "status": "pending"}
                    for r in insight.get("recommendations", [])
                ],
            )

            goals.append(goal)
            self.goals[goal.goal_id] = goal

        self._save_strategy()
        logger.info(f"🎯 Created {len(goals)} strategic goals from insights")
        return goals

    async def create_initiative(
        self, name: str, description: str, goal_ids: list[str], expected_impact: float
    ) -> StrategicInitiative:
        """Create a strategic initiative from goals."""
        goals = [self.goals[gid] for gid in goal_ids if gid in self.goals]

        initiative = StrategicInitiative(
            initiative_id=f"init_{hashlib.md5(name.encode()).hexdigest()[:8]}",
            name=name,
            description=description,
            goals=goals,
            expected_impact=expected_impact,
            status="planning",
        )

        self.initiatives[initiative.initiative_id] = initiative
        self._save_strategy()

        logger.info(f"📦 Created initiative: {name} with {len(goals)} goals")
        return initiative

    async def generate_roadmap(self, timeframe_days: int = 30) -> dict[str, Any]:
        """Generate strategic roadmap for the given timeframe."""
        roadmap = {
            "timeframe_days": timeframe_days,
            "generated_at": datetime.now().isoformat(),
            "initiatives": [],
            "goals_by_priority": {},
            "resource_allocation": {},
        }

        # Group goals by priority
        by_priority: dict[Priority, list[StrategicGoal]] = defaultdict(list)
        for goal in self.goals.values():
            if goal.status in ["pending", "in_progress"]:
                by_priority[goal.priority].append(goal)

        roadmap["goals_by_priority"] = {p.name: len(by_priority[p]) for p in Priority}

        # Create initiative for high-priority goals
        if by_priority.get(Priority.CRITICAL) or by_priority.get(Priority.HIGH):
            critical_goals = by_priority.get(Priority.CRITICAL, []) + by_priority.get(
                Priority.HIGH, []
            )
            roadmap["initiatives"].append(
                {
                    "name": "Priority Improvements",
                    "description": "Address critical and high-priority issues",
                    "goals": [g.goal_id for g in critical_goals],
                    "timeline": "Week 1-2",
                    "expected_impact": sum(g.progress for g in critical_goals)
                    / max(len(critical_goals), 1),
                }
            )

        # Resource allocation suggestions
        roadmap["resource_allocation"] = {
            "evolution_analysis": "30% - Pattern detection and fixes",
            "agent_optimization": "25% - High-performer template creation",
            "knowledge_integration": "20% - Graph construction",
            "new_capabilities": "25% - Meta-generator spec creation",
        }

        return roadmap

    async def update_goal_progress(
        self, goal_id: str, progress: float, task_updates: list[dict] | None = None
    ) -> StrategicGoal | None:
        """Update progress on a goal."""
        if goal_id not in self.goals:
            return None

        goal = self.goals[goal_id]
        goal.progress = progress

        if task_updates:
            for update in task_updates:
                for task in goal.tasks:
                    if task["task"] == update.get("task"):
                        task["status"] = update.get("status", task["status"])

        if progress >= 1.0:
            goal.status = "completed"
        elif progress > 0:
            goal.status = "in_progress"

        self._save_strategy()
        return goal

    async def execute_strategic_plan(self) -> dict[str, Any]:
        """Execute the current strategic plan."""
        results = {
            "executed_at": datetime.now().isoformat(),
            "initiatives_executed": 0,
            "goals_completed": 0,
            "goals_in_progress": 0,
            "new_insights_generated": 0,
        }

        # Execute in-progress goals
        for goal in self.goals.values():
            if goal.status == "in_progress":
                results["goals_in_progress"] += 1

                # Simulate execution - in real implementation, this would trigger systems
                logger.info(
                    f"📈 Executing goal: {goal.name} ({goal.progress * 100:.0f}%)"
                )

        # Generate new insights from execution
        results["new_insights_generated"] = len(
            [g for g in self.goals.values() if g.status == "completed"]
        )

        results["goals_completed"] = len(
            [g for g in self.goals.values() if g.status == "completed"]
        )

        results["initiatives_executed"] = len(
            [i for i in self.initiatives.values() if i.status == "in_progress"]
        )

        logger.info(
            f"📊 Execution complete: {results['goals_completed']} goals completed"
        )
        return results

    async def get_strategy_status(self) -> dict[str, Any]:
        """Get current strategy status."""
        by_status = {"pending": 0, "in_progress": 0, "completed": 0}
        by_priority = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for goal in self.goals.values():
            by_status[goal.status] = by_status.get(goal.status, 0) + 1
            by_priority[goal.priority.name] += 1

        return {
            "total_goals": len(self.goals),
            "by_status": by_status,
            "by_priority": by_priority,
            "total_initiatives": len(self.initiatives),
            "overall_progress": sum(g.progress for g in self.goals.values())
            / max(len(self.goals), 1),
        }


async def main():
    """Demo strategy orchestration."""
    logging.basicConfig(level=logging.INFO)

    orchestrator = StrategyOrchestrator()

    # Create sample goals from insights
    sample_insights = [
        {
            "pattern_id": "test_001",
            "pattern_type": "test_coverage",
            "description": "Increase test coverage by 20%",
            "impact_score": 0.8,
            "recommendations": ["Generate tests with Mycelium", "Review test quality"],
        },
        {
            "pattern_id": "agent_002",
            "pattern_type": "agent_improvement",
            "description": "Optimize agent performance",
            "impact_score": 0.6,
            "recommendations": ["Review agent specs", "Update templates"],
        },
    ]

    await orchestrator.synthesize_goals_from_insights(sample_insights)

    # Create initiative
    await orchestrator.create_initiative(
        name="Quality Improvement Initiative",
        description="Improve overall system quality through testing and optimization",
        goal_ids=list(orchestrator.goals.keys())[:2],
        expected_impact=0.75,
    )

    # Generate roadmap
    roadmap = await orchestrator.generate_roadmap()
    print("\n" + "=" * 60)
    print("📋 STRATEGIC ROADMAP")
    print("=" * 60)
    print(json.dumps(roadmap, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
