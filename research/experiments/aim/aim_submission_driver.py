#!/usr/bin/env python3
"""
AIMO Production Submission Driver

Integrates all breakthrough components for production submission:
- Semantic cache (token efficiency)
- Context-aware solver (adaptive strategies)
- Experiential learning (continuous improvement)
- Ralph Loop coherence gating
- Kaggle submission API

Generates submission.parquet for Kaggle leaderboard.
"""

import argparse
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl
from context_aware_solver import get_solver
from experiential_learning import get_learning_engine
from failure_logger import FailureLogger
from semantic_cache import CachePersistence, get_cache
from swarm_coordinator import SwarmCoordinator


logger = logging.getLogger(__name__)


class AIMOSubmissionDriver:
    """
    Production submission driver for Kaggle AIMO competition.

    Workflow:
    1. Warm cache and learning
    2. Process test.csv (Kaggle evaluation protocol)
    3. Generate submission.parquet
    4. Log results for continuous improvement
    """

    def __init__(
        self,
        cache_max_entries: int = 512,
        vault_path: str = "~/vaults/cohezion-vault/regions/cerebrum/aimo",
        session_id: Optional[str] = None,
        output_dir: str = "output",
    ):
        self.session_id = session_id or f"submission_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.vault_path = Path(vault_path).expanduser()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        logger.info("Initializing production submission driver...")

        self.cache = get_cache(
            max_entries=cache_max_entries,
            vault_path=str(self.vault_path / "cache"),
        )
        logger.info(f"  Cache: {cache_max_entries} entries")

        self.solver = get_solver()
        logger.info("  Context-aware solver: initialized")

        self.learning_engine = get_learning_engine()
        logger.info("  Experiential learning: initialized")

        self.failure_logger = FailureLogger()
        logger.info("  Failure logger: initialized")

        self.coordinator = SwarmCoordinator()

        # Submission state
        self.submission_results: List[Dict[str, Any]] = []
        self.submission_start = time.time()

    def warm_start(self) -> Dict[str, Any]:
        """Warm start: load cache and learning."""
        logger.info("\nWarming up for submission...")

        persistence = CachePersistence()
        entries_loaded = persistence.warm_cache(self.cache)
        logger.info(f"  Cache warmed: {entries_loaded} entries")

        learning_summary = self.learning_engine.get_learning_summary()
        logger.info(f"  Learning: {learning_summary['total_experiences']} experiences")

        return {
            "cache_entries": entries_loaded,
            "experiences": learning_summary["total_experiences"],
        }

    def solve_problem(
        self,
        problem_id: str,
        problem_text: str,
    ) -> int:
        """Solve single problem for submission."""
        logger.info(f"\nProblem: {problem_id}")

        start_time = time.time()

        # Get problem context
        task = self.coordinator.plan_journey(problem_id, problem_text)
        problem_type = self._infer_problem_type(task.state)

        # Get strategy recommendation
        rec = self.learning_engine.get_strategy_recommendation(problem_type)
        logger.info(f"  Type: {problem_type}, Strategy: {rec['recommended_strategy']}")

        # Solve with context awareness
        answer, response, metadata = self.solver.solve(problem_id, problem_text)

        duration = time.time() - start_time

        # Record experience
        self.learning_engine.record_experience(
            problem_id=problem_id,
            problem_type=problem_type,
            strategy_used=metadata.get("strategy", "unknown"),
            success=True,  # Assume success for submission
            accuracy=1.0,
            coherence=metadata.get("coherence", 0.0),
            tokens_used=metadata.get("tokens_used", 0),
            duration_seconds=duration,
        )

        # Log result
        cache_str = " (cached)" if metadata.get("from_cache") else ""
        logger.info(f"  Answer: {answer}{cache_str}, Time: {duration:.1f}s")

        return answer or 0

    def _infer_problem_type(self, state) -> str:
        """Infer problem type from state."""
        scores = {
            "algebra": state.algebra,
            "number_theory": state.number_theory,
            "geometry": state.geometry,
            "combinatorics": state.combinatorics,
        }
        return max(scores, key=scores.get)

    def run_submission(
        self,
        test_csv: str = "input/test.csv",
        output_file: str = "output/submission.parquet",
    ) -> Dict[str, Any]:
        """
        Run complete submission pipeline.

        Args:
            test_csv: Path to test.csv (Kaggle format)
            output_file: Path for submission.parquet

        Returns:
            Submission summary
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"AIMO Production Submission: {self.session_id}")
        logger.info(f"{'=' * 60}")

        # Warm start
        warm_info = self.warm_start()

        # Load test data
        test_df = pl.read_csv(test_csv)
        logger.info(f"\nLoaded {len(test_df)} problems from {test_csv}")

        # Process each problem
        for idx in range(len(test_df)):
            problem_id = test_df[idx, "id"]
            problem_text = test_df[idx, "problem"]

            answer = self.solve_problem(problem_id, problem_text)

            self.submission_results.append(
                {
                    "id": problem_id,
                    "answer": answer,
                }
            )

        # Generate submission file
        submission_df = pl.DataFrame(self.submission_results)
        submission_df.write_parquet(output_file)
        logger.info(f"\nSubmission saved to: {output_file}")

        # Session summary
        duration = time.time() - self.submission_start
        summary = {
            "session_id": self.session_id,
            "duration_seconds": duration,
            "problems_solved": len(self.submission_results),
            "output_file": output_file,
            "cache_stats": self.cache.get_stats(),
            "learning_summary": self.learning_engine.get_learning_summary(),
            "efficiency_stats": self.solver.get_efficiency_stats(),
        }

        self._print_summary(summary)
        self._save_summary(summary)

        # Save cache
        persistence = CachePersistence()
        persistence.save_cache(self.cache)
        logger.info("Cache snapshot saved")

        # Export learning
        export_path = self.learning_engine.export_for_skill_refinement()
        logger.info(f"Learning exported: {export_path}")

        return summary

    def _print_summary(self, summary: Dict[str, Any]):
        """Print submission summary."""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Submission Summary")
        logger.info(f"{'=' * 60}")
        logger.info(f"Session: {summary['session_id']}")
        logger.info(f"Duration: {summary['duration_seconds'] / 60:.1f}m")
        logger.info(f"Problems: {summary['problems_solved']}")
        logger.info(
            f"Cache hits: {summary['cache_stats']['hits']} ({summary['cache_stats']['hit_rate'] * 100:.1f}%)"
        )
        logger.info(f"Tokens used: {summary['efficiency_stats']['tokens_used']}")
        logger.info(f"Tokens saved: ~{summary['cache_stats']['tokens_saved_estimate']}")
        logger.info(f"Cost savings: {summary['efficiency_stats']['estimated_cost_savings']}")
        logger.info(f"{'=' * 60}")

    def _save_summary(self, summary: Dict[str, Any]):
        """Save submission summary."""
        summary_file = self.output_dir / f"{self.session_id}_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="AIMO Production Submission Driver")
    parser.add_argument("--test-csv", type=str, default="input/test.csv", help="Test CSV path")
    parser.add_argument(
        "--output", type=str, default="output/submission.parquet", help="Output parquet path"
    )
    parser.add_argument("--cache-size", type=int, default=512, help="Cache max entries")
    parser.add_argument("--session-id", type=str, help="Session ID")
    parser.add_argument(
        "--vault",
        type=str,
        default="~/vaults/cohezion-vault/regions/cerebrum/aimo",
        help="Vault path",
    )

    args = parser.parse_args()

    # Run submission
    driver = AIMOSubmissionDriver(
        cache_max_entries=args.cache_size,
        session_id=args.session_id,
        vault_path=args.vault,
        output_dir=str(Path(args.output).parent),
    )

    summary = driver.run_submission(
        test_csv=args.test_csv,
        output_file=args.output,
    )

    print(f"\n{'=' * 60}")
    print(f"Submission Complete")
    print(f"{'=' * 60}")
    print(f"Output: {summary['output_file']}")
    print(f"Problems: {summary['problems_solved']}")
    print(f"Cache hit rate: {summary['cache_stats']['hit_rate'] * 100:.1f}%")
    print(f"Token efficiency: {summary['efficiency_stats']['efficiency_ratio'] * 100:.1f}%")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
