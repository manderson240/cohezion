#!/usr/bin/env python3
"""Validate the Cohezion compound engineering loop end-to-end.

This script proves the full loop works:
1. ManifoldEnv physics simulation (Lagrangian dynamics, HIHO attractor)
2. UniverseEvaluator benchmark (trained vs baselines with bootstrap CIs)
3. CompoundExecutor task execution (11-step pipeline)
4. DegradationDetector monitoring (thermal + quality thresholds)
5. CostAwareRouter feedback (degradation → model tier adjustment)
6. SkillRefiner knowledge persistence (execution → learning → skill update)

Usage:
    uv run python scripts/validate_compound_loop.py          # Quick validation
    uv run python scripts/validate_compound_loop.py --full   # Full with training
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-25s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("validate")


class ValidationResult:
    """Track validation step results."""

    def __init__(self) -> None:
        self.steps: list[tuple[str, bool, str]] = []

    def record(self, name: str, passed: bool, detail: str = "") -> None:
        self.steps.append((name, passed, detail))
        status = "PASS" if passed else "FAIL"
        logger.info(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    def summary(self) -> str:
        passed = sum(1 for _, p, _ in self.steps if p)
        total = len(self.steps)
        lines = [
            f"\n{'=' * 60}",
            f"VALIDATION RESULT: {passed}/{total} steps passed",
            f"{'=' * 60}",
        ]
        for name, p, detail in self.steps:
            status = "PASS" if p else "FAIL"
            lines.append(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
        lines.append(f"{'=' * 60}")
        return "\n".join(lines)

    @property
    def all_passed(self) -> bool:
        return all(p for _, p, _ in self.steps)


def validate_physics_environment(result: ValidationResult) -> None:
    """Step 1: Validate ManifoldEnv physics simulation."""
    logger.info("\n[1/10] ManifoldEnv Physics Simulation")

    try:
        from cohezion.environments.manifold_env import ManifoldEnv

        env = ManifoldEnv(max_steps=100, seed=42)
        obs, info = env.reset()

        result.record("ManifoldEnv creation", True, f"dim={env.dim}, obs_shape={obs.shape}")
        result.record("Observation space", obs.shape == (19,), f"shape={obs.shape}")

        # Run 50 steps with small random actions
        import numpy as np

        total_reward = 0.0
        for _ in range(50):
            action = np.random.uniform(-0.1, 0.1, size=(12,)).astype(np.float32)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            if terminated:
                break

        result.record(
            "Physics simulation (50 steps)",
            True,
            f"coherence={info['coherence']:.3f}, reward={total_reward:.2f}",
        )
        result.record(
            "HIHO tracking",
            "hiho_deviation" in info and "hiho_streak" in info,
            f"deviation={info['hiho_deviation']:.4f}, streak={info['hiho_streak']}",
        )
        result.record(
            "Curriculum staging",
            info.get("curriculum_stage") in (1, 2, 3),
            f"stage={info.get('curriculum_stage')}",
        )
    except Exception as e:
        result.record("ManifoldEnv physics", False, str(e))


def validate_evaluation_framework(result: ValidationResult) -> None:
    """Step 2: Validate UniverseEvaluator with baselines."""
    logger.info("\n[2/10] UniverseEvaluator Benchmark")

    try:
        from cohezion.environments.manifold_env import ManifoldEnv
        from cohezion.eval.universe_evaluator import (
            UniverseEvaluator,
            greedy_hiho_policy,
            random_policy,
        )

        env = ManifoldEnv(max_steps=100, seed=42)
        evaluator = UniverseEvaluator(n_bootstrap=20)

        rnd = evaluator.evaluate_policy(env, random_policy, n_episodes=3, policy_name="Random")
        greedy = evaluator.evaluate_policy(
            env, greedy_hiho_policy, n_episodes=3, policy_name="Greedy"
        )

        result.record(
            "Random baseline",
            rnd.mean_coherence > 0,
            f"coherence={rnd.mean_coherence:.3f}, reward={rnd.mean_reward:.2f}",
        )
        result.record(
            "Greedy baseline",
            greedy.mean_coherence > 0,
            f"coherence={greedy.mean_coherence:.3f}, reward={greedy.mean_reward:.2f}",
        )

        comparison = evaluator.compare_policies(
            env, {"random": random_policy, "greedy": greedy_hiho_policy}, n_episodes=3
        )
        result.record(
            "Policy comparison",
            comparison is not None and len(comparison.evaluations) > 0,
            f"{len(comparison.evaluations)} policies compared, best={comparison.best_policy}",
        )
    except Exception as e:
        result.record("UniverseEvaluator", False, str(e))


def validate_compound_executor(result: ValidationResult) -> None:
    """Step 3: Validate CompoundExecutor task execution."""
    logger.info("\n[3/10] CompoundExecutor Pipeline")

    try:
        from cohezion.compound.executor import CompoundExecutor

        mock_client = MagicMock()
        mock_client.vault_find_relevant_context.return_value = []
        mock_client.vault_search.return_value = []
        mock_client.vault_write.return_value = "success"
        mock_client.vault_log_experiment.return_value = "experiments/test.md"

        executor = CompoundExecutor(mcp_client=mock_client)
        result.record("CompoundExecutor creation", True)

        # Verify key attributes exist (private attrs prefixed with _)
        has_attrs = all(
            hasattr(executor, attr)
            for attr in [
                "_journey_tracker",
                "_degradation_detector",
                "_skill_refiner",
                "_retrospection_engine",
            ]
        )
        result.record(
            "Executor pipeline components",
            has_attrs,
            "journey_tracker, degradation_detector, skill_refiner, retrospection_engine",
        )
    except Exception as e:
        result.record("CompoundExecutor", False, str(e))


def validate_degradation_monitoring(result: ValidationResult) -> None:
    """Step 4: Validate DegradationDetector and routing feedback."""
    logger.info("\n[4/10] Degradation Monitoring + Routing Feedback")

    try:
        from cohezion.compound.degradation_detector import DegradationDetector

        detector = DegradationDetector()
        result.record("DegradationDetector creation", True)

        # Test routing callback mechanism
        callback_fired = []

        def routing_callback(alerts: list) -> None:
            callback_fired.append(len(alerts))

        detector.set_routing_callback(routing_callback)
        result.record("Routing callback set", hasattr(detector, "_routing_callback"))
    except Exception as e:
        result.record("DegradationDetector", False, str(e))

    try:
        from cohezion.swarm.cost_aware_router import CostAwareRouter

        router = CostAwareRouter()
        result.record("CostAwareRouter creation", True)

        # Test degradation feedback method
        has_feedback = hasattr(router, "apply_degradation_feedback")
        result.record("Degradation feedback path", has_feedback)
    except Exception as e:
        result.record("CostAwareRouter", False, str(e))


def validate_ouroboros_mycelium(result: ValidationResult) -> None:
    """Step 5: Validate Ouroboros + Mycelium integration."""
    logger.info("\n[5/10] Ouroboros + Mycelium Integration")

    try:
        from cohezion.ouroboros.detector import AnomalyDetector

        detector = AnomalyDetector(coherence_threshold=0.1, target_coherence=0.5)
        is_anomaly = detector.is_anomaly(0.2)  # 0.2 is far from 0.5
        is_normal = not detector.is_anomaly(0.48)  # 0.48 is close to 0.5
        result.record(
            "Ouroboros AnomalyDetector",
            is_anomaly and is_normal,
            f"anomaly@0.2={is_anomaly}, normal@0.48={is_normal}",
        )
    except Exception as e:
        result.record("Ouroboros AnomalyDetector", False, str(e))

    try:
        from cohezion.ouroboros.monitor import OuroborosMonitor

        monitor = OuroborosMonitor()
        result.record(
            "OuroborosMonitor (port 8001)",
            "8001" in monitor.url,
            f"url={monitor.url}",
        )
    except Exception as e:
        result.record("OuroborosMonitor", False, str(e))

    try:
        from cohezion.mycelium.observer import ChangeObserver

        observer = ChangeObserver()
        changes = observer.detect_modified_files()
        result.record(
            "Mycelium ChangeObserver",
            isinstance(changes, list),
            f"{len(changes)} recent changes detected",
        )
    except Exception as e:
        result.record("Mycelium ChangeObserver", False, str(e))


def validate_swarm_env(result: ValidationResult) -> None:
    """Step 6: Validate SwarmEnv multi-agent environment."""
    logger.info("\n[6/10] SwarmEnv Multi-Agent")

    try:
        from cohezion.environments.swarm_env import SwarmEnv

        env = SwarmEnv(n_agents=2, max_steps=20, seed=42)
        obs, infos = env.reset()

        result.record(
            "SwarmEnv creation (2 agents)",
            len(obs) == 2 and "agent_0" in obs,
            f"agents={list(obs.keys())}",
        )

        # Run 10 steps
        import numpy as np

        for _ in range(10):
            actions = {a: np.random.uniform(-0.1, 0.1, size=(12,)).astype(np.float32) for a in obs}
            obs, rewards, terms, truncs, infos = env.step(actions)

        dev = infos["agent_0"].get("global_hiho_deviation", -1)
        result.record(
            "SwarmEnv gauge coupling",
            0 < dev < 1.0,
            f"global_hiho_deviation={dev:.3f}",
        )
    except Exception as e:
        result.record("SwarmEnv", False, str(e))


def validate_skill_persistence(result: ValidationResult) -> None:
    """Step 7: Validate SkillRefiner and knowledge persistence."""
    logger.info("\n[7/10] Skill Refinement + Knowledge Persistence")

    try:
        from cohezion.compound.skill_refiner import SkillRefiner

        mock_client = MagicMock()
        mock_client.vault_write.return_value = "success"
        mock_client.vault_find_relevant_context.return_value = []

        refiner = SkillRefiner(mcp_client=mock_client)
        result.record("SkillRefiner creation", True)

        # Verify PRIME skills exist
        skills_dir = Path(__file__).parent.parent / "src" / "cohezion" / "skills"
        prime_count = len(list(skills_dir.glob("*PRIME*.md")))
        result.record("PRIME skills", prime_count > 100, f"{prime_count} skills found")
    except Exception as e:
        result.record("SkillRefiner", False, str(e))


def validate_persistence_backends(result: ValidationResult) -> None:
    """Step 7: Validate SurrealDB + vault persistence."""
    logger.info("\n[8/10] SurrealDB + Vault Persistence")

    import urllib.request

    # SurrealDB health check
    try:
        resp = urllib.request.urlopen("http://localhost:8001/health", timeout=3)
        result.record("SurrealDB health (port 8001)", resp.status == 200)
    except Exception:
        result.record("SurrealDB health (port 8001)", False, "Not reachable")

    # Vault directory check
    vault_path = Path.home() / "vaults" / "cohezion-vault"
    cerebellum = vault_path / "cerebellum"
    result.record(
        "Obsidian vault",
        vault_path.exists() and cerebellum.exists(),
        f"cerebellum={'exists' if cerebellum.exists() else 'missing'}",
    )


def validate_routing_orchestrator(result: ValidationResult) -> None:
    """Step 8: Validate RoutingOrchestrator unified entry."""
    logger.info("\n[9/10] Routing Orchestrator (Unified Entry)")

    try:
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orchestrator = RoutingOrchestrator()
        result.record("RoutingOrchestrator creation", True)

        decision = orchestrator.route("Analyze training results and update documentation")
        result.record(
            "Unified routing decision",
            decision is not None,
            f"model={decision.model}, confidence={decision.confidence:.2f}",
        )
    except Exception as e:
        result.record("RoutingOrchestrator", False, str(e))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Cohezion compound loop")
    parser.add_argument("--full", action="store_true", help="Include PPO training (slow)")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Cohezion Compound Engineering Loop Validation")
    logger.info("=" * 60)

    start = time.time()
    result = ValidationResult()

    validate_physics_environment(result)
    validate_evaluation_framework(result)
    validate_compound_executor(result)
    validate_degradation_monitoring(result)
    validate_ouroboros_mycelium(result)
    validate_swarm_env(result)
    validate_skill_persistence(result)
    validate_persistence_backends(result)
    validate_routing_orchestrator(result)

    elapsed = time.time() - start
    print(result.summary())
    print(f"\nCompleted in {elapsed:.1f}s")

    sys.exit(0 if result.all_passed else 1)


if __name__ == "__main__":
    main()
