"""
Charter-aligned skill analytics with EDL routing.
Complex refinements go through Expert Domain Lattice.
"""

from datetime import datetime, timedelta

from pydantic import BaseModel

from cohezion.core.persistence.surreal_client import get_surreal_client
from cohezion.platform.edl_router import get_edl_router
from cohezion.platform.observable_action import get_observable_proposer
from cohezion.platform.skill_scorer_charter import (
    get_skill_scorer,
)


class CharterSkillInsights(BaseModel):
    """Skill insights with Charter compliance."""

    top_hiho_stable: list[str]  # Skills maintaining HIHO stability
    hiho_unstable: list[str]  # Skills outside 0.4-0.6 range
    failing_skills: list[str]  # <50% success rate
    refinement_candidates: list[str]  # Require EDL review
    compound_patterns: list[dict]


class CharterAlignedSkillAnalytics:
    """Analytics with EDL routing for complex decisions."""

    def __init__(self):
        self.db = get_surreal_client()
        self.scorer = get_skill_scorer()
        self.edl_router = get_edl_router()
        self.observable_proposer = get_observable_proposer()

    async def generate_insights(self, days: int = 7) -> CharterSkillInsights:
        """Generate insights with Charter compliance."""

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 1. Top HIHO-stable skills
        result = await self.db.query(
            """
            SELECT skill_name, math::mean(hiho_stability) as avg_hiho
            FROM skill_metrics_charter
            WHERE date >= type::datetime($start_date)
              AND date < type::datetime($end_date)
            GROUP BY skill_name
            HAVING avg_hiho >= 0.8  -- Strong HIHO stability
            ORDER BY avg_hiho DESC
            LIMIT 5;
        """,
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        top_hiho_stable = [row["skill_name"] for row in result]

        # 2. HIHO unstable skills (Charter violation)
        result = await self.db.query(
            """
            SELECT skill_name, math::mean(avg_coherence) as avg_coherence
            FROM skill_metrics_charter
            WHERE date >= type::datetime($start_date)
              AND date < type::datetime($end_date)
            GROUP BY skill_name
            HAVING (avg_coherence < 0.4 OR avg_coherence > 0.6)
            ORDER BY math::abs(avg_coherence - 0.5) DESC;
        """,
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        hiho_unstable = [row["skill_name"] for row in result]

        # 3. Failing skills
        result = await self.db.query(
            """
            SELECT skill_name, math::mean(success_rate) as avg_success
            FROM skill_metrics_charter
            WHERE date >= type::datetime($start_date)
              AND date < type::datetime($end_date)
            GROUP BY skill_name
            HAVING avg_success < 0.5
            ORDER BY avg_success ASC;
        """,
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        failing_skills = [row["skill_name"] for row in result]

        # 4. Refinement candidates (complex cases → EDL)
        # Skills that are both HIHO unstable AND failing
        refinement_candidates = list(set(hiho_unstable) & set(failing_skills))

        # 5. Compound patterns (simplified for initial implementation)
        compound_patterns = []

        return CharterSkillInsights(
            top_hiho_stable=top_hiho_stable,
            hiho_unstable=hiho_unstable,
            failing_skills=failing_skills,
            refinement_candidates=refinement_candidates,
            compound_patterns=compound_patterns,
        )

    async def propose_skill_refinement(
        self, skill_name: str, reason: str, approval_callback=None
    ) -> bool:
        """
        Propose skill refinement using Observable AI + EDL consensus.

        Charter Compliance:
        1. Route complex decisions through EDL
        2. Display reasoning before action (Observable AI)
        3. Require approval for low confidence

        Returns:
            True if refinement approved and executed, False otherwise
        """

        # Get skill metrics for context
        metrics = await self._get_skill_metrics(skill_name)

        # Route through EDL for consensus
        consensus = await self.edl_router.route_decision(
            decision_type="architecture",  # Skill refinement is architectural
            context=f"Skill: {skill_name}\nReason: {reason}\nMetrics: {metrics}",
            proposal=f"Refine skill {skill_name} to improve HIHO stability and success rate",
        )

        # Propose action with Observable AI
        async def refine_skill():
            # Actual refinement logic would go here
            print(f"Refining skill: {skill_name}")

        approved = await self.observable_proposer.propose_action(
            action_type="refactor",
            description=f"Refine skill {skill_name}",
            rationale=f"{reason}\nEDL Consensus: {consensus.consensus_strength:.2f}",
            confidence=consensus.consensus_strength,
            action_fn=refine_skill,
            risks=[
                "Skill behavior may change",
                "Existing integrations need testing",
            ],
            benefits=[
                "Improved HIHO stability",
                "Higher success rate",
                "Better token efficiency",
            ],
            reversible=True,
            approval_callback=approval_callback,
        )

        return approved

    async def _get_skill_metrics(self, skill_name: str) -> str:
        """Get recent metrics for a skill as formatted string."""
        result = await self.db.query(
            """
            SELECT *
            FROM skill_metrics_charter
            WHERE skill_name = $skill_name
            ORDER BY date DESC
            LIMIT 7;
        """,
            {"skill_name": skill_name},
        )

        if not result:
            return "No metrics available"

        metrics_lines = []
        for row in result:
            metrics_lines.append(
                f"  {row['date']}: effectiveness={row['effectiveness_score']:.2f}, "
                f"hiho={row['hiho_stability']:.2f}, success={row['success_rate']:.2f}"
            )

        return "\n".join(metrics_lines)


# Singleton accessor
_skill_analytics = None


def get_skill_analytics() -> CharterAlignedSkillAnalytics:
    """Get global Charter-aligned skill analytics instance."""
    global _skill_analytics
    if _skill_analytics is None:
        _skill_analytics = CharterAlignedSkillAnalytics()
    return _skill_analytics


def reset_skill_analytics():
    """Reset global skill analytics (for testing)."""
    global _skill_analytics
    _skill_analytics = None
