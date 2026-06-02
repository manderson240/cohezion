"""Decoupled Dual-Loop Optimization for self-evolving agent swarms.

Based on arXiv:2605.30621. Disentangles policy prompt updating (Outer Loop)
from verification harness synthesis (Inner Loop) to prevent policy decay.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from cohezion.compound.harness_benefit import HarnessBenefitTracker


logger = logging.getLogger(__name__)


class DualLoopOptimizer:
    """Manages decoupled optimization of agent policies and verification harnesses."""

    def __init__(
        self,
        harness_synthesizer: Any,
        benefit_tracker: HarnessBenefitTracker | None = None,
    ) -> None:
        """
        Parameters
        ----------
        harness_synthesizer : AutoHarnessSynthesizer
            An instance of AutoHarnessSynthesizer.
        benefit_tracker : HarnessBenefitTracker | None
            Tracker for logs and adherence delta records.
        """
        self.synthesizer = harness_synthesizer
        self.tracker = benefit_tracker or HarnessBenefitTracker()

    async def evaluate_adherence_delta(
        self,
        policy_fn: Callable[[Any], Any],
        harness_fn: Callable[[Any, Any], bool] | None,
        dataset: list[dict[str, Any]],
        metric_fn: Callable[[Any, Any], float],
    ) -> float:
        """Calculate the Adherence Delta of a harness against a frozen policy.

        Adherence Delta = Score(Policy with Harness) - Score(Policy without Harness)

        Parameters
        ----------
        policy_fn : Callable
            The policy prediction function (maps state -> action).
        harness_fn : Callable | None
            The verification harness function (maps (state, action) -> bool).
            If None, represents the unharnessed raw policy.
        dataset : list[dict]
            Evaluation dataset containing states and target values.
        metric_fn : Callable
            A metric function that evaluates (action, target) -> float (0.0 to 1.0).

        Returns
        -------
        float
            The Adherence Delta score.
        """
        total_score = 0.0
        for sample in dataset:
            state = sample["state"]
            target = sample["target"]

            # 1. Run policy
            action = policy_fn(state)

            # 2. Apply harness check if present
            if harness_fn is not None:
                # If verifier rejects, we try a fallback action or penalize score
                is_valid = harness_fn(state, action)
                if not is_valid:
                    # In a real system, verifier rejection triggers regeneration or fallback.
                    # For metrics, a rejected action gets a score of 0.0 or a default action is taken.
                    action = sample.get("fallback_action", None)

            score = metric_fn(action, target)
            total_score += score

        return total_score / len(dataset) if dataset else 0.0

    async def optimize_cycle(
        self,
        skill_name: str,
        environment_desc: str,
        policy_fn: Callable[[Any], Any],
        raw_score: float,
        dataset: list[dict[str, Any]],
        metric_fn: Callable[[Any, Any], float],
        dummy_env: Callable[[str], tuple[bool, str]],
    ) -> dict[str, Any]:
        """Execute one complete decoupled optimization cycle.

        Outer Loop: Run policy updates (prompt tuning) under a frozen harness.
        Inner Loop: Search and synthesize verification harnesses under a frozen policy.

        Parameters
        ----------
        skill_name : str
            The name of the PRIME skill to optimize.
        environment_desc : str
            The description of the environment rules.
        policy_fn : Callable
            The policy prediction function.
        raw_score : float
            Baseline quality score of the raw policy.
        dataset : list[dict]
            Evaluation dataset.
        metric_fn : Callable
            Quality metric function.
        dummy_env : Callable
            AutoHarness verification environment callback.

        Returns
        -------
        dict
            Results dictionary containing the status of the loops.
        """
        # Step 1: Record pre-refinement baseline
        self.tracker.record_pre_execution(skill_name, raw_score)

        # Step 2: Inner Loop — Optimize Verification Harness
        logger.info("[DualLoop] Starting Inner Loop: Harness Synthesis...")
        verifier_code = await self.synthesizer.synthesize_verifier(environment_desc, dummy_env)

        # Create python callable from verifier_code (for local evaluation)
        local_namespace: dict[str, Any] = {}
        try:
            exec(verifier_code, local_namespace)  # noqa: S102
            harness_fn = local_namespace.get("verify_action")
        except Exception as e:
            logger.error("Failed to compile synthesized verifier: %s", e)
            harness_fn = None

        # Step 3: Evaluate Adherence Delta
        harnessed_score = await self.evaluate_adherence_delta(
            policy_fn=policy_fn,
            harness_fn=harness_fn,
            dataset=dataset,
            metric_fn=metric_fn,
        )

        adherence_delta = harnessed_score - raw_score
        logger.info(
            "[DualLoop] Inner Loop complete. Adherence Delta: %.4f (Raw: %.4f, Harnessed: %.4f)",
            adherence_delta,
            raw_score,
            harnessed_score,
        )

        # Step 4: Record post-refinement execution
        self.tracker.record_post_execution(
            skill_name=skill_name,
            quality_score=harnessed_score,
            model_tier="local",
            instruction_length_delta=len(verifier_code),
        )
        self.tracker.record_invocation(skill_name)

        return {
            "skill_name": skill_name,
            "verifier_code": verifier_code,
            "adherence_delta": adherence_delta,
            "raw_score": raw_score,
            "harnessed_score": harnessed_score,
            "success": harnessed_score >= raw_score,
        }
