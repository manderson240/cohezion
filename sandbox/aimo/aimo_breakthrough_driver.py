#!/usr/bin/env python3
"""
AIMO Breakthrough Driver - Compound Engineering Integration

Integrates:
- Semantic cache (60-80% token reduction)
- Context-aware solving (adaptive strategies)
- Experiential learning (continuous improvement)
- Ralph Loop coherence gating
- Compound session management

Achieves breakthroughs through:
1. Token efficiency → More problems per session
2. Context awareness → Better strategy selection
3. Experiential learning → Continuous improvement
4. Compound engineering → Long-horizon execution
"""

import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from context_aware_solver import get_solver
from experiential_learning import get_learning_engine
from failure_logger import FailureLogger
from semantic_cache import CachePersistence, get_cache
from swarm_coordinator import SwarmCoordinator


logger = logging.getLogger(__name__)


class AIMOBreakthroughDriver:
    """
    Breakthrough driver integrating all compound engineering components.

    Workflow:
    1. Warm cache (load from snapshot)
    2. Load learning engine (past experiences)
    3. For each problem:
       - Check cache
       - Select optimal strategy
       - Solve with context awareness
       - Record experience
       - Update patterns
    4. Save cache snapshot
    5. Export learning for skill refinement
    """

    def __init__(
        self,
        cache_max_entries: int = 256,
        vault_path: str = "~/vaults/cohezion-vault/regions/cerebrum/aimo",
        session_id: Optional[str] = None,
    ):
        self.session_id = session_id or f"breakthrough_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.vault_path = Path(vault_path).expanduser()
        self.vault_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        logger.info("Initializing breakthrough driver...")

        self.cache = get_cache(
            max_entries=cache_max_entries,
            vault_path=str(self.vault_path / "cache"),
        )
        logger.info(f"  Cache initialized (max {cache_max_entries} entries)")

        self.solver = get_solver()
        logger.info("  Context-aware solver initialized")

        self.learning_engine = get_learning_engine()
        logger.info("  Experiential learning engine initialized")

        self.failure_logger = FailureLogger()
        logger.info("  Failure logger initialized")

        self.coordinator = SwarmCoordinator()

        # Session state
        self.problems_solved = 0
        self.session_start = time.time()
        self.session_results: List[Dict[str, Any]] = []

    def warm_start(self) -> Dict[str, Any]:
        """Warm start: load cache and learning."""
        logger.info("\nWarming up session...")

        # Warm cache
        persistence = CachePersistence()
        entries_loaded = persistence.warm_cache(self.cache)
        logger.info(f"  Cache warmed: {entries_loaded} entries")

        # Load learning
        learning_summary = self.learning_engine.get_learning_summary()
        logger.info(f"  Learning: {learning_summary['total_experiences']} experiences loaded")

        return {
            "cache_entries": entries_loaded,
            "experiences_loaded": learning_summary["total_experiences"],
        }

    def solve_problem(
        self,
        problem_id: str,
        problem_text: str,
        expected_answer: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Solve single problem with full context awareness."""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Problem: {problem_id}")
        logger.info(f"{'=' * 60}")

        start_time = time.time()

        # Get problem context
        task = self.coordinator.plan_journey(problem_id, problem_text)
        problem_type = self._infer_problem_type(task.state)

        # Get strategy recommendation from learning engine
        rec = self.learning_engine.get_strategy_recommendation(problem_type)
        logger.info(f"  Problem type: {problem_type}")
        logger.info(
            f"  Recommended strategy: {rec['recommended_strategy']} (confidence: {rec['confidence']:.2f})"
        )
        if rec["lessons"]:
            logger.info(f"  Lessons: {rec['lessons'][:2]}")  # Top 2 lessons

        # Solve
        answer, response, metadata = self.solver.solve(problem_id, problem_text)

        duration = time.time() - start_time

        # Check correctness
        correct = (answer == expected_answer) if expected_answer is not None else None

        # Record experience
        self.learning_engine.record_experience(
            problem_id=problem_id,
            problem_type=problem_type,
            strategy_used=metadata.get("strategy", "unknown"),
            success=correct if correct is not None else (metadata.get("coherence", 0) > 0.5),
            accuracy=1.0 if correct else 0.0,
            coherence=metadata.get("coherence", 0.0),
            tokens_used=metadata.get("tokens_used", 0),
            duration_seconds=duration,
            lessons_learned=self._extract_lessons(metadata, correct),
        )

        # Update session state
        self.problems_solved += 1

        result = {
            "problem_id": problem_id,
            "problem_type": problem_type,
            "answer": answer,
            "expected": expected_answer,
            "correct": correct,
            "coherence": metadata.get("coherence", 0.0),
            "from_cache": metadata.get("from_cache", False),
            "strategy": metadata.get("strategy", "unknown"),
            "tokens_used": metadata.get("tokens_used", 0),
            "duration": duration,
        }

        self.session_results.append(result)

        # Log result
        status = "✅" if correct else "❌" if correct is False else "?"
        cache_str = " (cached)" if metadata.get("from_cache") else ""
        logger.info(f"  {status} Answer: {answer}{cache_str}")
        logger.info(f"  Time: {duration:.1f}s, Tokens: {metadata.get('tokens_used', 0)}")

        return result

    def _infer_problem_type(self, state) -> str:
        """Infer problem type from state."""
        scores = {
            "algebra": state.algebra,
            "number_theory": state.number_theory,
            "geometry": state.geometry,
            "combinatorics": state.combinatorics,
        }
        return max(scores, key=scores.get)

    def _extract_lessons(self, metadata: Dict[str, Any], correct: Optional[bool]) -> List[str]:
        """Extract lessons from solving experience."""
        lessons = []

        if metadata.get("from_cache"):
            lessons.append("Cache hit - strategy effective for this problem type")

        if metadata.get("coherence", 0) > 0.8:
            lessons.append(f"High coherence ({metadata['coherence']:.2f}) - maintain this approach")

        if metadata.get("coherence", 0) < 0.3:
            lessons.append(
                f"Low coherence ({metadata['coherence']:.2f}) - try alternative strategy"
            )

        if metadata.get("tie_breaker_used"):
            lessons.append("Tie-breaker required - consider ensemble strategy")

        if correct is False:
            lessons.append("Incorrect answer - review failure pattern")

        return lessons

    def run_session(
        self,
        problems: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Run breakthrough session on problems."""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"AIMO Breakthrough Session: {self.session_id}")
        logger.info(f"{'=' * 60}")
        logger.info(f"Problems: {len(problems)}")
        logger.info(f"{'=' * 60}\n")

        # Warm start
        warm_info = self.warm_start()

        # Solve each problem
        for i, problem in enumerate(problems, 1):
            logger.info(f"\nProblem {i}/{len(problems)}")
            self.solve_problem(
                problem_id=problem.get("id", f"problem_{i}"),
                problem_text=problem["problem"],
                expected_answer=problem.get("answer"),
            )

        # Session summary
        summary = self._get_session_summary()
        self._print_summary(summary)

        # Save results
        self._save_session(summary)

        # Export learning
        export_path = self.learning_engine.export_for_skill_refinement()
        logger.info(f"\nLearning exported to: {export_path}")

        # Save cache
        persistence = CachePersistence()
        persistence.save_cache(self.cache)
        logger.info("Cache snapshot saved")

        return summary

    def _get_session_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        duration = time.time() - self.session_start

        correct_count = sum(1 for r in self.session_results if r.get("correct"))
        cached_count = sum(1 for r in self.session_results if r.get("from_cache"))

        total_tokens = sum(r.get("tokens_used", 0) for r in self.session_results)
        cache_stats = self.cache.get_stats()

        return {
            "session_id": self.session_id,
            "duration_seconds": duration,
            "problems_solved": len(self.session_results),
            "correct_count": correct_count,
            "accuracy": correct_count / len(self.session_results) if self.session_results else 0.0,
            "cached_count": cached_count,
            "cache_hit_rate": cached_count / len(self.session_results)
            if self.session_results
            else 0.0,
            "total_tokens_used": total_tokens,
            "tokens_saved_estimate": cache_stats["tokens_saved_estimate"],
            "avg_coherence": sum(r.get("coherence", 0) for r in self.session_results)
            / len(self.session_results)
            if self.session_results
            else 0.0,
            "efficiency_stats": self.solver.get_efficiency_stats(),
            "learning_summary": self.learning_engine.get_learning_summary(),
        }

    def _print_summary(self, summary: Dict[str, Any]):
        """Print session summary."""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Session Summary: {summary['session_id']}")
        logger.info(f"{'=' * 60}")
        logger.info(f"Duration: {summary['duration_seconds'] / 60:.1f}m")
        logger.info(f"Problems: {summary['problems_solved']}")
        logger.info(
            f"Accuracy: {summary['accuracy'] * 100:.1f}% ({summary['correct_count']}/{summary['problems_solved']})"
        )
        logger.info(
            f"Cache hits: {summary['cached_count']} ({summary['cache_hit_rate'] * 100:.1f}%)"
        )
        logger.info(f"Tokens used: {summary['total_tokens_used']}")
        logger.info(f"Tokens saved: ~{summary['tokens_saved_estimate']}")
        logger.info(f"Avg coherence: {summary['avg_coherence']:.3f}")
        logger.info(f"Cost savings: {summary['efficiency_stats']['estimated_cost_savings']}")
        logger.info(f"{'=' * 60}")

    def _save_session(self, summary: Dict[str, Any]):
        """Save session results."""
        session_dir = self.vault_path / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)

        # Save summary
        summary_file = session_dir / f"{self.session_id}_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        # Save detailed results
        results_file = session_dir / f"{self.session_id}_results.json"
        with open(results_file, "w") as f:
            json.dump(self.session_results, f, indent=2)

        logger.info(f"Session saved to: {session_dir}")


def main():
    parser = argparse.ArgumentParser(description="AIMO Breakthrough Driver")
    parser.add_argument("--problems", type=int, default=10, help="Number of problems")
    parser.add_argument("--cache-size", type=int, default=256, help="Cache max entries")
    parser.add_argument("--session-id", type=str, help="Session ID")
    parser.add_argument(
        "--vault",
        type=str,
        default="~/vaults/cohezion-vault/regions/cerebrum/aimo",
        help="Vault path",
    )

    args = parser.parse_args()

    # Load problems
    problems_file = Path("reference_problems.json")
    if not problems_file.exists():
        logger.error("reference_problems.json not found")
        return

    with open(problems_file) as f:
        all_problems = json.load(f)

    problems = all_problems[: args.problems]

    # Run session
    driver = AIMOBreakthroughDriver(
        cache_max_entries=args.cache_size,
        session_id=args.session_id,
        vault_path=args.vault,
    )

    summary = driver.run_session(problems)

    print(f"\n{'=' * 60}")
    print(f"Breakthrough Session Complete")
    print(f"{'=' * 60}")
    print(f"Accuracy: {summary['accuracy'] * 100:.1f}%")
    print(f"Cache hit rate: {summary['cache_hit_rate'] * 100:.1f}%")
    print(f"Token efficiency: {summary['efficiency_stats']['efficiency_ratio'] * 100:.1f}%")
    print(f"Learning: {summary['learning_summary']['total_experiences']} experiences")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
