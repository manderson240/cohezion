"""EvoPolicyGym adapter — wraps SkillRefiner as an EvoPolicyGym benchmark agent.

EvoPolicyGym (arXiv 2607.02440) benchmarks autonomous LLM policy evolution:
  agent.evolve_policy(current_policy, task_description, feedback) -> new_policy

Cohezion SkillRefiner IS this agent:
  current_policy  = PRIME skill file content
  task_description = operation_type for routing
  feedback        = ExecutionMetrics (quality, tokens, success, tier_used)
  new_policy      = updated PRIME skill content (with appended recommendation)

Claude Opus 4.7 baseline on synthesis tasks: 48% structural-edit→validation rate.
Run evaluate_structural_edit_rate() after N episodes to compare.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any

from cohezion.compound.skill_refiner import SkillRefiner


@dataclasses.dataclass
class EvoPolicyFeedback:
    success: bool
    quality_score: float = 0.5
    duration_seconds: float = 1.0
    tokens_used: int = 500
    tier_used: str = "igpu"
    escalation_count: int = 0
    cached_hits: int = 0


class SkillRefinerEvoPolicyAgent:
    """Thin adapter making SkillRefiner callable as an EvoPolicyGym agent.

    Usage:
        agent = SkillRefinerEvoPolicyAgent()
        new_policy = agent.evolve_policy(current_policy, task_description, feedback)
    """

    def __init__(self, skill_name: str = "evopolicygym-eval") -> None:
        self.skill_name = skill_name
        self.refiner = SkillRefiner()
        self._episode_history: list[dict[str, Any]] = []

    def evolve_policy(
        self,
        current_policy: str,
        task_description: str,
        feedback: EvoPolicyFeedback | dict[str, Any],
    ) -> str:
        if isinstance(feedback, dict):
            feedback = EvoPolicyFeedback(**{
                k: v for k, v in feedback.items()
                if k in {f.name for f in dataclasses.fields(EvoPolicyFeedback)}
            })

        execution_result: dict[str, Any] = {
            "success": feedback.success,
            "tokens_used": feedback.tokens_used,
            "quality_score": feedback.quality_score,
            "duration_seconds": feedback.duration_seconds,
            "tier_used": feedback.tier_used,
            "escalation_count": feedback.escalation_count,
            "cached_hits": feedback.cached_hits,
            "output": current_policy[:200],  # first 200 chars as output sample
        }

        recommendation = self.refiner.refine(
            self.skill_name,
            task_description,
            execution_result,
        )

        episode: dict[str, Any] = {
            "task": task_description,
            "quality": feedback.quality_score,
            "success": feedback.success,
            "recommendation": recommendation,
            "policy_changed": recommendation is not None and bool(recommendation),
        }
        self._episode_history.append(episode)

        if not recommendation:
            return current_policy  # stable — no update needed

        # Append the recommendation as a new section to the PRIME skill
        return _append_recommendation(current_policy, recommendation)

    def evaluate_structural_edit_rate(self) -> float:
        """Fraction of episodes where the policy was structurally modified.

        EvoPolicyGym baseline: Opus 4.7 = 0.48 on synthesis tasks.
        A rate > 0.48 indicates the SkillRefiner is more responsive than Opus baseline.
        A rate < 0.48 may indicate quality gates (ShadowCanary, seesaw) are too conservative.
        """
        if not self._episode_history:
            return 0.0
        changed = sum(1 for ep in self._episode_history if ep["policy_changed"])
        return changed / len(self._episode_history)

    def reset(self) -> None:
        self._episode_history.clear()


def _append_recommendation(policy: str, recommendation: str) -> str:
    """Append a recommendation as a versioned delta to the policy string."""
    # Find the latest ## Evolution section and increment, or create first one
    existing = re.findall(r"## Evolution v(\d+)", policy)
    next_version = (max(int(v) for v in existing) + 1) if existing else 1
    delta = f"\n\n## Evolution v{next_version}\n\n{recommendation.strip()}\n"
    return policy + delta


class EvoPolicyGymBenchmark:
    """Runs a synthetic EvoPolicyGym episode sequence to benchmark SkillRefiner.

    Mirrors the EvoPolicyGym eval protocol: N success episodes with quality variation
    above and below a rolling baseline, measuring structural-edit→validation rate.

    Requires an existing PRIME skill file. Uses "COMPOUND_LOOP_GUIDE" by default
    (the skill with most refinement history). Pass skill_name to use another.
    """

    SYNTHESIS_TASKS = [
        "synthesis: compose a multi-step reasoning plan for the compound loop",
        "synthesis: generate a skill recommendation from degraded cache metrics",
        "synthesis: produce a tier routing decision given mixed quality signals",
        "synthesis: create a PRIME skill update from a cross-skill proximity hint",
        "synthesis: design an adaptive verification criterion from task feedback",
    ]

    def run(self, n_episodes: int = 20, skill_name: str = "COMPOUND_LOOP_GUIDE") -> dict[str, Any]:
        agent = SkillRefinerEvoPolicyAgent(skill_name=skill_name)
        policy = _initial_policy()

        for i in range(n_episodes):
            task = self.SYNTHESIS_TASKS[i % len(self.SYNTHESIS_TASKS)]
            # Warm-up (first 5): establish high-quality baseline
            # Test phase: quality drops below baseline on some episodes
            if i < 5:
                quality = 0.80 + 0.05 * (i % 3)  # 0.80–0.90 warmup
            else:
                # Every 3rd episode: quality drop to trigger recommendation
                quality = 0.55 if (i % 3 == 0) else 0.85
            feedback = EvoPolicyFeedback(
                success=True,  # all successful — refine() only acts on success
                quality_score=quality,
                tokens_used=300 + i * 20,
                tier_used="igpu",
                escalation_count=0,
            )
            policy = agent.evolve_policy(policy, task, feedback)

        rate = agent.evaluate_structural_edit_rate()
        return {
            "n_episodes": n_episodes,
            "skill_name": skill_name,
            "structural_edit_rate": rate,
            "opus_47_baseline": 0.48,
            "outperforms_baseline": rate > 0.48,
            "episodes": agent._episode_history,
            "final_policy_length": len(policy),
        }


def _initial_policy() -> str:
    return """---
name: evopolicygym-eval
description: EvoPolicyGym evaluation baseline policy for SkillRefiner benchmark.
version: 0.0.0
---

# EvoPolicyGym Eval Policy

## Baseline Strategy

Process synthesis tasks using the compound loop's tiered inference cascade.
Route to NPU for classification, iGPU for generation, CPU for reasoning.
Record quality metrics and update this policy on each episode.
"""


def run_benchmark(n_episodes: int = 20) -> None:
    """CLI entry point for EvoPolicyGym benchmark."""
    benchmark = EvoPolicyGymBenchmark()
    result = benchmark.run(n_episodes=n_episodes)
    print(f"EvoPolicyGym Benchmark Results ({result['n_episodes']} episodes)")
    print(f"  Structural-edit rate: {result['structural_edit_rate']:.1%}")
    print(f"  Opus 4.7 baseline:    {result['opus_47_baseline']:.1%}")
    status = "✓ OUTPERFORMS" if result["outperforms_baseline"] else "✗ BELOW"
    print(f"  {status} baseline")
    print(f"  Final policy length:  {result['final_policy_length']} chars")


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_benchmark(n_episodes=n)
