#!/usr/bin/env python3
"""Ralph Loop main for autonomous kernel optimization.

Integrates Ralph Loop coherence gating with K-Search autoresearch driver.

Usage:
    uv run python ralph_main.py --kernel gemm --max-cycles 100
    uv run python ralph_main.py --kernel all --max-cycles 50
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ralph_main")


RALPH_CONFIG = {
    "coherence_threshold": 0.5,
    "max_iterations": 100,
    "stagnation_threshold": 7,
    "leaderboard_targets": {
        "gemm": 4.327,
        "moe": 109.793,
        "mla": 32.972,
    },
}

BASE_DIR = Path(__file__).parent
VAULT_BASE = Path.home() / "vaults" / "cohezion-vault" / "luma-speedrun" / "autoresearch"


@dataclass
class CoherenceRecord:
    cycle: int
    accuracy: float
    stability: float
    alignment: float
    coherence: float
    result_us: float
    improvement_pct: float
    timestamp: str = ""


class RalphLoop:
    """Ralph Loop coherence gate for kernel optimization."""

    def __init__(
        self,
        kernel: str,
        coherence_threshold: float = 0.5,
        max_iterations: int = 100,
        stagnation_threshold: int = 7,
    ):
        self.kernel = kernel
        self.coherence_threshold = coherence_threshold
        self.max_iterations = max_iterations
        self.stagnation_threshold = stagnation_threshold

        self.cycle = 0
        self.best_us = float("inf")
        self.best_coherence = 0.0
        self.stagnation_count = 0
        self.coherence_history: list[CoherenceRecord] = []

        self.vault_path = VAULT_BASE / kernel
        self._ensure_vault()

    def _ensure_vault(self):
        """Ensure vault directory exists."""
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def compute_coherence(
        self,
        result_us: float,
        previous_best: float,
        per_shape_results: dict[str, float],
        strategy_alignment: float = 0.5,
    ) -> CoherenceRecord:
        """Compute HIHO coherence score."""
        # Accuracy: improvement over previous best
        if previous_best == float("inf"):
            accuracy = 0.5
        elif result_us < previous_best:
            improvement = (previous_best - result_us) / previous_best
            accuracy = min(1.0, improvement * 5)
        else:
            accuracy = max(0.0, 1.0 - (result_us - previous_best) / previous_best)

        # Stability: inverse of coefficient of variation
        if per_shape_results:
            values = list(per_shape_results.values())
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std_dev = math.sqrt(variance)
            cv = std_dev / mean if mean > 0 else 0
            stability = max(0.0, 1.0 - cv)
        else:
            stability = 0.5

        alignment = strategy_alignment
        coherence = accuracy * 0.5 + stability * 0.3 + alignment * 0.2

        improvement_pct = (
            ((previous_best - result_us) / previous_best * 100)
            if previous_best != float("inf") and previous_best > 0
            else 0.0
        )

        return CoherenceRecord(
            cycle=self.cycle,
            accuracy=accuracy,
            stability=stability,
            alignment=alignment,
            coherence=coherence,
            result_us=result_us,
            improvement_pct=improvement_pct,
            timestamp=datetime.now().isoformat(),
        )

    def check_hiho_gate(self, coherence: float) -> bool:
        """Check HIHO coherence gate."""
        passed = coherence >= self.coherence_threshold
        log.info(
            f"[{self.kernel}] HIHO gate: coherence={coherence:.3f} "
            f"(threshold={self.coherence_threshold}) → {'PASS' if passed else 'FAIL'}"
        )
        return passed

    def check_breakthrough(self, result_us: float) -> bool:
        """Check if Rank 1 target achieved."""
        target = RALPH_CONFIG["leaderboard_targets"].get(self.kernel, 0)
        if target > 0 and result_us <= target:
            log.info(f"[{self.kernel}] BREAKTHROUGH! {result_us:.1f}µs <= {target:.1f}µs target!")
            return True
        return False

    def check_stagnation(self, result_us: float) -> bool:
        """Check if stagnating (no improvement for K cycles)."""
        if result_us < self.best_us:
            self.stagnation_count = 0
            return False
        self.stagnation_count += 1
        if self.stagnation_count >= self.stagnation_threshold:
            log.info(
                f"[{self.kernel}] STAGNATION: {self.stagnation_count} cycles without improvement"
            )
        return self.stagnation_count >= self.stagnation_threshold

    def log_cycle(self, record: CoherenceRecord, mutation: str = ""):
        """Log cycle to vault."""
        try:
            log_file = self.vault_path / "ralph_log.jsonl"
            entry = {
                "kernel": self.kernel,
                "cycle": record.cycle,
                "timestamp": record.timestamp,
                "result_us": record.result_us,
                "coherence": record.coherence,
                "accuracy": record.accuracy,
                "stability": record.stability,
                "improvement_pct": record.improvement_pct,
                "best_us": self.best_us,
                "stagnation_count": self.stagnation_count,
                "mutation": mutation,
            }
            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

            # Update state
            state_file = self.vault_path / "state.json"
            state = {
                "kernel": self.kernel,
                "best_us": self.best_us,
                "best_coherence": self.best_coherence,
                "stagnation_count": self.stagnation_count,
                "total_cycles": self.cycle,
                "updated": datetime.now().isoformat(),
            }
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            log.warning(f"Failed to log to vault: {e}")

    def run(self, cycle_fn, per_shape_fn=None) -> dict[str, Any]:
        """
        Run Ralph Loop until breakthrough or max iterations.

        Args:
            cycle_fn: Function that runs one optimization cycle.
                     Must accept cycle_num and return (success, result_us)
            per_shape_fn: Optional function that returns per-shape results dict

        Returns:
            Final summary dict
        """
        target = RALPH_CONFIG["leaderboard_targets"].get(self.kernel, 0)
        log.info(f"Starting Ralph Loop for {self.kernel}")
        log.info(f"Target: {target:.1f}µs (Rank 1)")
        log.info(f"Coherence threshold: {self.coherence_threshold}")
        log.info(f"Max iterations: {self.max_iterations}")
        log.info(f"Stagnation threshold: {self.stagnation_threshold}")

        for i in range(self.max_iterations):
            self.cycle = i + 1
            previous_best = self.best_us

            log.info(f"\n{'=' * 50}")
            log.info(f"Cycle {self.cycle}/{self.max_iterations}")
            log.info(f"{'=' * 50}")

            try:
                success, result_us = cycle_fn(self.cycle)
            except Exception as e:
                log.error(f"Cycle failed: {e}")
                success = False
                result_us = float("inf")

            # Get per-shape results if available
            per_shape = {}
            if per_shape_fn:
                try:
                    per_shape = per_shape_fn()
                except Exception:
                    pass

            # Compute coherence
            record = self.compute_coherence(
                result_us=result_us,
                previous_best=previous_best,
                per_shape_results=per_shape,
            )

            # Update best
            if result_us < self.best_us:
                self.best_us = result_us
                log.info(f"New best: {self.best_us:.1f}µs")
            if record.coherence > self.best_coherence:
                self.best_coherence = record.coherence

            # Check gates
            stagnation = self.check_stagnation(result_us)
            breakthrough = self.check_breakthrough(result_us)
            gate_passed = self.check_hiho_gate(record.coherence)

            mutation = ""
            if stagnation:
                mutation = "R-Zero: stagnation detected"
                log.info(f"  → Triggering R-Zero challenger")
            elif not gate_passed:
                mutation = f"Low coherence ({record.coherence:.2f} < {self.coherence_threshold})"
                log.info(f"  → Proposing mutation")

            # Log to vault
            self.log_cycle(record, mutation)

            # Check exit conditions
            if breakthrough:
                log.info(f"\n{'=' * 50}")
                log.info(f"BREAKTHROUGH! Rank 1 achieved: {self.best_us:.1f}µs")
                log.info(f"Target was: {target:.1f}µs")
                log.info(f"{'=' * 50}")
                break

            if self.cycle >= self.max_iterations:
                log.info(f"\nMax iterations ({self.max_iterations}) reached")
                break

            time.sleep(1)  # Brief pause between cycles

        # Final summary
        summary = {
            "kernel": self.kernel,
            "total_cycles": self.cycle,
            "best_us": self.best_us,
            "best_coherence": self.best_coherence,
            "target_us": target,
            "gap_to_target": self.best_us - target if target > 0 else None,
            "stagnation_count": self.stagnation_count,
            "breakthrough": self.best_us <= target if target > 0 else False,
        }

        log.info(f"\n{'=' * 50}")
        log.info(f"RALPH LOOP COMPLETE: {self.kernel}")
        log.info(f"  Best: {self.best_us:.1f}µs")
        log.info(f"  Target: {target:.1f}µs")
        log.info(
            f"  Gap: {summary['gap_to_target']:.1f}µs" if summary["gap_to_target"] else "  Gap: N/A"
        )
        log.info(f"  Cycles: {self.cycle}")
        log.info(f"  Breakthrough: {summary['breakthrough']}")
        log.info(f"{'=' * 50}")

        return summary


def run_gemm_cycle(cycle_num: int) -> tuple[bool, float]:
    """Run one GEMM optimization cycle."""
    from driver import load_tree, rate_limiter, run_cycle, save_tree

    tree = load_tree("gemm")
    success, summary = run_cycle("gemm", tree, rate_limiter, dry_run=False)
    save_tree(tree)

    try:
        result_us = float(summary.split(":")[1].split("µs")[0].strip())
    except Exception:
        result_us = float("inf")

    return success, result_us


def run_moe_cycle(cycle_num: int) -> tuple[bool, float]:
    """Run one MoE optimization cycle."""
    from driver import load_tree, rate_limiter, run_cycle, save_tree

    tree = load_tree("moe")
    success, summary = run_cycle("moe", tree, rate_limiter, dry_run=False)
    save_tree(tree)

    try:
        result_us = float(summary.split(":")[1].split("µs")[0].strip())
    except Exception:
        result_us = float("inf")

    return success, result_us


def run_mla_cycle(cycle_num: int) -> tuple[bool, float]:
    """Run one MLA optimization cycle."""
    from driver import load_tree, rate_limiter, run_cycle, save_tree

    tree = load_tree("mla")
    success, summary = run_cycle("mla", tree, rate_limiter, dry_run=False)
    save_tree(tree)

    try:
        result_us = float(summary.split(":")[1].split("µs")[0].strip())
    except Exception:
        result_us = float("inf")

    return success, result_us


def main():
    parser = argparse.ArgumentParser(description="Ralph Loop autonomous kernel optimizer")
    parser.add_argument(
        "--kernel",
        required=True,
        choices=["gemm", "moe", "mla", "all"],
        help="Kernel to optimize",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=100,
        help="Max iterations per kernel (default: 100)",
    )
    parser.add_argument(
        "--coherence-threshold",
        type=float,
        default=0.5,
        help="HIHO coherence threshold (default: 0.5)",
    )
    parser.add_argument(
        "--stagnation-threshold",
        type=int,
        default=7,
        help="Stagnation threshold K (default: 7)",
    )
    args = parser.parse_args()

    kernels = ["gemm", "moe", "mla"] if args.kernel == "all" else [args.kernel]

    results = {}
    for kernel in kernels:
        log.info(f"\n\n{'#' * 60}")
        log.info(f"# KERNEL: {kernel}")
        log.info(f"{'#' * 60}")

        ralph = RalphLoop(
            kernel=kernel,
            coherence_threshold=args.coherence_threshold,
            max_iterations=args.max_cycles,
            stagnation_threshold=args.stagnation_threshold,
        )

        if kernel == "gemm":
            result = ralph.run(run_gemm_cycle)
        elif kernel == "moe":
            result = ralph.run(run_moe_cycle)
        else:
            result = ralph.run(run_mla_cycle)

        results[kernel] = result

    # Final summary
    log.info(f"\n\n{'=' * 60}")
    log.info("RALPH LOOP SUMMARY")
    log.info(f"{'=' * 60}")
    for kernel, result in results.items():
        log.info(f"  {kernel}: {result['best_us']:.1f}µs (target: {result['target_us']:.1f}µs)")
        if result["breakthrough"]:
            log.info(f"    → BREAKTHROUGH!")
        else:
            gap = result.get("gap_to_target")
            if gap:
                log.info(f"    → Gap: {gap:.1f}µs to target")


if __name__ == "__main__":
    main()
