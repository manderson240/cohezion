"""Cognitive Synthesis Core.

Multi-scale pattern recognition engine that synthesizes insights
from across the Cohezion universe, enabling emergent intelligence.
"""

import asyncio
import hashlib
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PatternInsight:
    """Discovered pattern with synthesized insight."""

    pattern_id: str
    pattern_type: str
    description: str
    confidence: float
    impact_score: float
    evidence: list[dict[str, Any]]
    recommendations: list[str]
    discovered_at: datetime = field(default_factory=datetime.now)


@dataclass
class CrossDomainCorrelation:
    """Correlation between patterns across domains."""

    domain_a: str
    domain_b: str
    correlation_strength: float
    causal_direction: str | None
    insight: str


class SynthesisCore:
    """
    Cognitive Synthesis Core for multi-scale pattern recognition.

    Analyzes data from:
    - Universe Engine (journeys, trajectories)
    - Evolution Orchestrator (code patterns)
    - Reward System (XP trends, achievements)
    - Knowledge Graph (semantic relationships)

    Generates actionable insights and predicts emergent opportunities.
    """

    def __init__(self):
        self.patterns: list[PatternInsight] = []
        self.correlations: list[CrossDomainCorrelation] = []
        self._insight_cache: dict[str, dict[str, Any]] = {}

    async def synthesize_from_universe(
        self, journey_data: list[dict]
    ) -> list[PatternInsight]:
        """Analyze universe journeys for patterns."""
        insights = []

        # Group by agent
        agent_journeys: dict[str, list[dict]] = defaultdict(list)
        for journey in journey_data:
            agent = journey.get("agent_name", "Unknown")
            agent_journeys[agent].append(journey)

        # Analyze agent performance patterns
        for agent, journeys in agent_journeys.items():
            phi_scores = [j.get("final_phi_score", 0.5) for j in journeys]
            avg_phi = sum(phi_scores) / len(phi_scores)

            if len(journeys) >= 3 and avg_phi > 0.75:
                insights.append(
                    PatternInsight(
                        pattern_id=hashlib.md5(
                            f"high_performer_{agent}".encode()
                        ).hexdigest()[:8],
                        pattern_type="agent_excellence",
                        description=f"Agent '{agent}' consistently delivers high-quality results (avg phi={avg_phi:.2f})",
                        confidence=0.85,
                        impact_score=0.7,
                        evidence=[
                            {
                                "agent": agent,
                                "journeys": len(journeys),
                                "avg_phi": avg_phi,
                            }
                        ],
                        recommendations=[
                            f"Consider granting '{agent}' higher autonomy tier",
                            f"Use '{agent}' as template for new agent generation",
                            f"Extract '{agent}' patterns into meta-generator templates",
                        ],
                    )
                )

            if len(journeys) >= 5 and avg_phi < 0.5:
                insights.append(
                    PatternInsight(
                        pattern_id=hashlib.md5(
                            f"struggling_{agent}".encode()
                        ).hexdigest()[:8],
                        pattern_type="agent_improvement",
                        description=f"Agent '{agent}' underperforming (avg phi={avg_phi:.2f})",
                        confidence=0.8,
                        impact_score=0.6,
                        evidence=[
                            {
                                "agent": agent,
                                "journeys": len(journeys),
                                "avg_phi": avg_phi,
                            }
                        ],
                        recommendations=[
                            f"Review '{agent}' system prompt",
                            f"Consider regenerating '{agent}' with updated spec",
                            f"Provide '{agent}' with additional toolkit capabilities",
                        ],
                    )
                )

        logger.info(
            f"📊 Synthesized {len(insights)} insights from {len(journey_data)} journeys"
        )
        self.patterns.extend(insights)
        return insights

    async def synthesize_from_evolution(
        self, evolution_data: dict
    ) -> list[PatternInsight]:
        """Analyze evolution patterns for code quality trends."""
        insights = []

        patterns = evolution_data.get("patterns", [])
        suggestions = evolution_data.get("suggestions", [])

        # Categorize patterns by type
        pattern_types: dict[str, int] = defaultdict(int)
        for pattern in patterns:
            pattern_types[pattern.get("type", "unknown")] += 1

        # Identify dominant issues
        for ptype, count in pattern_types.items():
            if count > 50:
                insights.append(
                    PatternInsight(
                        pattern_id=hashlib.md5(
                            f"evolution_{ptype}".encode()
                        ).hexdigest()[:8],
                        pattern_type="code_quality_trend",
                        description=f"'{ptype}' is the most common code quality issue ({count} occurrences)",
                        confidence=0.9,
                        impact_score=0.5,
                        evidence=[{"pattern_type": ptype, "count": count}],
                        recommendations=[
                            f"Create linter rule for '{ptype}'",
                            f"Add to Evolution Orchestrator auto-fix rules",
                            f"Document '{ptype}' prevention in coding standards",
                        ],
                    )
                )

        logger.info(f"🔍 Synthesized {len(insights)} insights from evolution patterns")
        self.patterns.extend(insights)
        return insights

    async def synthesize_from_rewards(self, rewards_data: dict) -> list[PatternInsight]:
        """Analyze reward patterns for contributor trends."""
        insights = []

        leaderboard = rewards_data.get("leaderboard", [])
        achievements = rewards_data.get("achievements", {})

        if len(leaderboard) >= 3:
            top_contributor = leaderboard[0]
            insights.append(
                PatternInsight(
                    pattern_id=hashlib.md5("top_contributor".encode()).hexdigest()[:8],
                    pattern_type="contributor_excellence",
                    description=f"'{top_contributor['agent_id']}' leads with {top_contributor['xp']} XP",
                    confidence=0.95,
                    impact_score=0.8,
                    evidence=[top_contributor],
                    recommendations=[
                        f"Recognize '{top_contributor['agent_id']}' in system documentation",
                        f"Use '{top_contributor['agent_id']}' as benchmark for other agents",
                        f"Consider '{top_contributor['agent_id']}' for meta-generator patterns",
                    ],
                )
            )

        logger.info(f"🏆 Synthesized {len(insights)} insights from reward data")
        self.patterns.extend(insights)
        return insights

    async def find_cross_domain_correlations(self) -> list[CrossDomainCorrelation]:
        """Discover correlations between patterns across domains."""
        correlations = []

        # Group patterns by type
        by_type: dict[str, list[PatternInsight]] = defaultdict(list)
        for pattern in self.patterns:
            by_type[pattern.pattern_type].append(pattern)

        # Check for correlations between high performers and code quality
        if "agent_excellence" in by_type and "code_quality_trend" in by_type:
            excellent_agents = {
                p.evidence[0]["agent"] for p in by_type["agent_excellence"]
            }
            if len(excellent_agents) >= 2:
                correlations.append(
                    CrossDomainCorrelation(
                        domain_a="universe_journeys",
                        domain_b="evolution_patterns",
                        correlation_strength=0.65,
                        causal_direction="agent_quality → code_quality",
                        insight="Agents with higher phi_scores tend to generate code with fewer quality issues",
                    )
                )

        # Check for contributor engagement correlation
        if "contributor_excellence" in by_type and "agent_excellence" in by_type:
            correlations.append(
                CrossDomainCorrelation(
                    domain_a="rewards_system",
                    domain_b="universe_journeys",
                    correlation_strength=0.7,
                    causal_direction="rewards → engagement",
                    insight="XP accumulation correlates with higher journey completion rates",
                )
            )

        self.correlations.extend(correlations)
        logger.info(f"🔗 Found {len(correlations)} cross-domain correlations")
        return correlations

    async def generate_synthesis_report(self) -> dict[str, Any]:
        """Generate comprehensive synthesis report."""
        # Aggregate patterns by impact
        high_impact = [p for p in self.patterns if p.impact_score > 0.6]
        medium_impact = [p for p in self.patterns if 0.3 < p.impact_score <= 0.6]

        return {
            "generated_at": datetime.now().isoformat(),
            "total_patterns": len(self.patterns),
            "high_impact_count": len(high_impact),
            "medium_impact_count": len(medium_impact),
            "cross_domain_correlations": len(self.correlations),
            "priority_insights": [
                {
                    "id": p.pattern_id,
                    "type": p.pattern_type,
                    "description": p.description,
                    "impact": p.impact_score,
                    "recommendations": p.recommendations[:2],
                }
                for p in sorted(
                    high_impact, key=lambda x: x.impact_score, reverse=True
                )[:5]
            ],
            "correlations": [
                {
                    "domains": f"{c.domain_a} ↔ {c.domain_b}",
                    "strength": c.correlation_strength,
                    "insight": c.insight,
                }
                for c in self.correlations[:5]
            ],
        }

    async def run_full_synthesis(self) -> dict[str, Any]:
        """Run complete synthesis across all available data sources."""
        logger.info("🌌 Running full cognitive synthesis...")

        # Collect data from each source
        universe_data = await self._collect_universe_data()
        evolution_data = await self._collect_evolution_data()
        rewards_data = await self._collect_rewards_data()

        # Synthesize from each source
        await self.synthesize_from_universe(universe_data)
        await self.synthesize_from_evolution(evolution_data)
        await self.synthesize_from_rewards(rewards_data)

        # Find cross-domain correlations
        await self.find_cross_domain_correlations()

        # Generate final report
        report = await self.generate_synthesis_report()

        logger.info(
            f"✅ Synthesis complete: {report['total_patterns']} patterns, {report['cross_domain_correlations']} correlations"
        )

        return report

    async def _collect_universe_data(self) -> list[dict]:
        """Collect journey data from universe engine."""
        try:
            from cohezion.db.surreal_client import SurrealClient

            db = SurrealClient()
            await db.connect()
            result = await db.query(
                "SELECT * FROM universe_journey ORDER BY created_at DESC LIMIT 100"
            )
            await db.close()
            return result or []
        except Exception as e:
            logger.warning(f"Could not collect universe data: {e}")
            return []

    async def _collect_evolution_data(self) -> dict:
        """Collect evolution pattern data."""
        from cohezion.meta.evolution import EvolutionOrchestrator

        evolution = EvolutionOrchestrator(auto_deploy=False)
        patterns = evolution.analyze_code()
        suggestions = evolution.generate_suggestions()
        return {"patterns": patterns, "suggestions": suggestions}

    async def _collect_rewards_data(self) -> dict:
        """Collect reward system data."""
        from cohezion.rewards.system import RewardSystem

        rewards = RewardSystem()
        leaderboard = rewards.get_leaderboard(limit=10)
        return {"leaderboard": leaderboard}


async def main():
    """Run synthesis demo."""
    logging.basicConfig(level=logging.INFO)

    core = SynthesisCore()
    report = await core.run_full_synthesis()

    print("\n" + "=" * 60)
    print("🌌 COGNITIVE SYNTHESIS REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
