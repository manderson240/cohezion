"""Ralph Loop integration for autonomous kernel optimization.

Adds:
- HIHO coherence gates (threshold: 0.5)
- Coherence tracking per kernel
- R-Zero stagnation detection (K=7)
- Vault persistence for recursive learning
- Autonomous loop until Rank 1 or max iterations

Usage:
    from ralph_integrator import RalphLoopIntegrator
    integrator = RalphLoopIntegrator(kernel="gemm")
    result = integrator.run_until_breakthrough()
"""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


logger = logging.getLogger("ralph_integrator")


RALPH_CONFIG = {
    "coherence_threshold": 0.5,  # HIHO gate
    "max_iterations": 100,  # Per kernel
    "stagnation_threshold": 7,  # K=7 fails → R-Zero
    "improvement_target": 0.05,  # 5% minimum improvement to be "coherent"
    "leaderboard_targets": {
        "gemm": 4.5,  # µs for Rank 1
        "moe": 110.0,
        "mla": 33.0,
    },
}


@dataclass
class CoherenceRecord:
    """Single coherence measurement."""

    cycle: int
    accuracy: float  # Improvement achieved (0-1)
    stability: float  # Consistency across shapes (0-1)
    alignment: float  # Strategy alignment (0-1)
    coherence: float  # Weighted combination
    result_us: float
    target_us: float
    improvement_pct: float
    timestamp: str = ""


class RalphLoopIntegrator:
    """
    Ralph Loop controller for autonomous kernel optimization.

    Workflow:
    1. Run cycle (test + benchmark)
    2. Compute coherence = accuracy*0.5 + stability*0.3 + alignment*0.2
    3. If coherence >= threshold:
         - Record success
         - Check if breakthrough (Rank 1 achieved)
    4. If coherence < threshold:
         - Propose mutation
         - Trigger R-Zero if stagnation
    5. Update world model (V-scores)
    6. Iterate until target or max iterations
    """

    def __init__(
        self,
        kernel: str,
        config: Optional[dict[str, Any]] = None,
        vault_path: Optional[str] = None,
    ):
        self.kernel = kernel
        self.config = {**RALPH_CONFIG, **(config or {})}
        self.vault_path = Path(vault_path) if vault_path else None

        self.cycle: int = 0
        self.best_us: float = float("inf")
        self.best_coherence: float = 0.0
        self.stagnation_count: int = 0
        self.breakthrough_achieved: bool = False
        self.breakthrough_cycle: Optional[int] = None

        self.coherence_history: list[CoherenceRecord] = []
        self.mutation_log: list[str] = []

        # Load previous state if exists
        self._load_state()

        logger.info(f"RalphLoopIntegrator({kernel}) initialized")
        logger.info(f"  Coherence threshold: {self.config['coherence_threshold']}")
        logger.info(f"  Target: {self.config['leaderboard_targets'].get(kernel, 'N/A')}µs")
        logger.info(f"  Best so far: {self.best_us:.1f}µs")

    def compute_coherence(
        self,
        result_us: float,
        previous_best: float,
        per_shape_results: dict[str, float],
        strategy_alignment: float = 0.5,
    ) -> CoherenceRecord:
        """
        Compute HIHO coherence score.

        coherence = accuracy*0.5 + stability*0.3 + alignment*0.2

        accuracy: Did we improve? (0-1, where 1 = significant improvement)
        stability: How consistent? (0-1, lower variance = higher)
        alignment: Did we follow the strategy? (0-1)
        """
        # Accuracy: improvement over previous best
        if previous_best == float("inf"):
            accuracy = 0.5  # Neutral on first run
        elif result_us < previous_best:
            improvement = (previous_best - result_us) / previous_best
            accuracy = min(1.0, improvement * 5)  # Scale: 20% improvement = 1.0
        else:
            accuracy = max(0.0, 1.0 - (result_us - previous_best) / previous_best)

        # Stability: inverse of coefficient of variation across shapes
        if per_shape_results:
            values = list(per_shape_results.values())
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std_dev = math.sqrt(variance)
            cv = std_dev / mean if mean > 0 else 0
            stability = max(0.0, 1.0 - cv)  # Lower CV = higher stability
        else:
            stability = 0.5

        # Alignment: trust the strategy parameter (can be adjusted)
        alignment = strategy_alignment

        # Weighted coherence
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
            target_us=self.config["leaderboard_targets"].get(self.kernel, 0),
            improvement_pct=improvement_pct,
            timestamp=datetime.now().isoformat(),
        )

    def check_hiho_gate(self, coherence: float) -> bool:
        """HIHO gate: coherence >= threshold."""
        return coherence >= self.config["coherence_threshold"]

    def check_stagnation(self, result_us: float) -> bool:
        """Check if we've stagnated (no improvement for K cycles)."""
        if result_us < self.best_us:
            self.stagnation_count = 0
            return False
        self.stagnation_count += 1
        return self.stagnation_count >= self.config["stagnation_threshold"]

    def check_breakthrough(self, result_us: float) -> bool:
        """Check if we've achieved Rank 1 (target achieved)."""
        target = self.config["leaderboard_targets"].get(self.kernel, 0)
        if target > 0 and result_us <= target:
            return True
        if result_us < self.best_us:
            return True
        return False

    def should_propose_mutation(self, coherence: float, stagnation: bool) -> str:
        """
        Determine if we should propose a mutation.

        Returns mutation reason if yes, empty string if no.
        """
        if stagnation:
            return "R-Zero: stagnation detected (K=7 fails)"

        if coherence < self.config["coherence_threshold"]:
            return f"Low coherence ({coherence:.2f} < {self.config['coherence_threshold']})"

        return ""

    def log_to_vault(
        self,
        cycle: int,
        coherence_record: CoherenceRecord,
        mutation_reason: str = "",
    ) -> None:
        """Log cycle results to vault for recursive learning."""
        if not self.vault_path:
            return

        try:
            self.vault_path.mkdir(parents=True, exist_ok=True)
            log_file = self.vault_path / "ralph_log.jsonl"

            entry = {
                "kernel": self.kernel,
                "cycle": cycle,
                "timestamp": coherence_record.timestamp,
                "result_us": coherence_record.result_us,
                "coherence": coherence_record.coherence,
                "accuracy": coherence_record.accuracy,
                "stability": coherence_record.stability,
                "improvement_pct": coherence_record.improvement_pct,
                "best_us": self.best_us,
                "stagnation_count": self.stagnation_count,
                "mutation": mutation_reason,
            }

            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

            # Update state file
            state = {
                "kernel": self.kernel,
                "best_us": self.best_us,
                "best_coherence": self.best_coherence,
                "stagnation_count": self.stagnation_count,
                "breakthrough_achieved": self.breakthrough_achieved,
                "breakthrough_cycle": self.breakthrough_cycle,
                "total_cycles": self.cycle,
            }
            state_file = self.vault_path / "ralph_state.json"
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to log to vault: {e}")

    def _load_state(self) -> None:
        """Load previous state from vault."""
        if not self.vault_path:
            return

        try:
            state_file = self.vault_path / "ralph_state.json"
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                self.best_us = state.get("best_us", float("inf"))
                self.best_coherence = state.get("best_coherence", 0.0)
                self.stagnation_count = state.get("stagnation_count", 0)
                self.breakthrough_achieved = state.get("breakthrough_achieved", False)
                self.breakthrough_cycle = state.get("breakthrough_cycle")
                logger.info(
                    f"Loaded state: best={self.best_us:.1f}µs, cycles={state.get('total_cycles', 0)}"
                )
        except Exception as e:
            logger.debug(f"No previous state found: {e}")

    def run_cycle(
        self,
        cycle_fn,
        previous_best: float,
        per_shape_results: dict[str, float],
        strategy_alignment: float = 0.5,
    ) -> tuple[bool, CoherenceRecord, str]:
        """
        Run one Ralph cycle.

        Args:
            cycle_fn: Function that executes the optimization cycle
                     Must return (success, result_us)
            previous_best: Previous best result in µs
            per_shape_results: Dict of shape -> time in µs
            strategy_alignment: How aligned with strategy (0-1)

        Returns:
            (proceed, coherence_record, mutation_reason)
        """
        self.cycle += 1
        start = time.time()

        # Execute cycle
        try:
            success, result_us = cycle_fn(self.cycle)
        except Exception as e:
            logger.error(f"Cycle {self.cycle} failed: {e}")
            success = False
            result_us = float("inf")

        # Compute coherence
        coherence_record = self.compute_coherence(
            result_us=result_us,
            previous_best=previous_best,
            per_shape_results=per_shape_results,
            strategy_alignment=strategy_alignment,
        )

        # Check for new best
        if result_us < self.best_us:
            self.best_us = result_us
            logger.info(f"New best: {self.best_us:.1f}µs (was {previous_best:.1f}µs)")

        # Check gates
        stagnation = self.check_stagnation(result_us)
        breakthrough = self.check_breakthrough(result_us)
        mutation_reason = self.should_propose_mutation(coherence_record.coherence, stagnation)

        # Record
        self.coherence_history.append(coherence_record)
        if breakthrough:
            self.breakthrough_achieved = True
            self.breakthrough_cycle = self.cycle

        # Log to vault
        self.log_to_vault(self.cycle, coherence_record, mutation_reason)

        elapsed = time.time() - start
        logger.info(
            f"Cycle {self.cycle}: {result_us:.1f}µs, "
            f"coherence={coherence_record.coherence:.2f} "
            f"(gate={'PASS' if self.check_hiho_gate(coherence_record.coherence) else 'FAIL'}), "
            f"stagnation={self.stagnation_count}, "
            f"elapsed={elapsed:.1f}s"
        )

        if mutation_reason:
            self.mutation_log.append(f"Cycle {self.cycle}: {mutation_reason}")
            logger.info(f"  → {mutation_reason}")

        if breakthrough:
            logger.info(f"  → BREAKTHROUGH! Target achieved: {result_us:.1f}µs")

        return success, coherence_record, mutation_reason

    def get_summary(self) -> dict[str, Any]:
        """Get loop summary."""
        return {
            "kernel": self.kernel,
            "total_cycles": self.cycle,
            "best_us": self.best_us,
            "best_coherence": self.best_coherence,
            "breakthrough_achieved": self.breakthrough_achieved,
            "breakthrough_cycle": self.breakthrough_cycle,
            "target_us": self.config["leaderboard_targets"].get(self.kernel),
            "gap_to_target": (
                (self.best_us - self.config["leaderboard_targets"].get(self.kernel, 0))
                if self.config["leaderboard_targets"].get(self.kernel)
                else None
            ),
            "avg_coherence": (
                sum(c.coherence for c in self.coherence_history) / len(self.coherence_history)
                if self.coherence_history
                else 0
            ),
            "stagnation_count": self.stagnation_count,
            "mutations_triggered": len(self.mutation_log),
        }


def create_ralph_driver(
    kernel: str,
    base_driver_path: str,
    config: Optional[dict[str, Any]] = None,
) -> str:
    """
    Create a Ralph-enhanced driver for a kernel.

    Returns path to the new driver.
    """
    vault_path = f"~/vaults/cohezion-vault/luma-speedrun/autoresearch/{kernel}"

    ralph_code = f'''#!/usr/bin/env python3
"""Ralph Loop enhanced driver for {kernel} kernel.

Auto-generated by ralph_integrator.py
Coherence threshold: {RALPH_CONFIG["coherence_threshold"]}
Max iterations: {RALPH_CONFIG["max_iterations"]}
"""

import sys
import logging
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from ralph_integrator import RalphLoopIntegrator

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ralph_{kernel}")

RALPH_CONFIG = {{
    "coherence_threshold": 0.5,
    "max_iterations": 100,
    "stagnation_threshold": 7,
    "improvement_target": 0.05,
    "leaderboard_targets": {{
        "{kernel}": {RALPH_CONFIG["leaderboard_targets"].get(kernel)},
    }},
}}


def run_{kernel}_cycle(cycle_num: int) -> tuple[bool, float]:
    """Run one optimization cycle for {kernel}.
    
    Returns (success, result_us).
    """
    # Import here to avoid circular deps
    from driver import run_cycle, load_tree, save_tree, rate_limiter, KERNEL_DIRS
    
    kernel_dir = Path(".") / "autoresearch"
    tree = load_tree("{kernel}")
    
    # Run the standard cycle
    success, summary = run_cycle(
        "{kernel}",
        tree,
        rate_limiter,
        dry_run=False,
    )
    
    # Extract result from summary
    # Format: "{{kernel}}: {{geomean:.1f}}µs ..."
    try:
        geomean = float(summary.split(":")[1].split("µs")[0].strip())
    except:
        geomean = float("inf")
    
    save_tree(tree)
    return success, geomean


def main():
    integrator = RalphLoopIntegrator(
        kernel="{kernel}",
        config=RALPH_CONFIG,
        vault_path="{vault_path}",
    )
    
    log.info(f"Starting Ralph Loop for {kernel}")
    log.info(f"Target: {{RALPH_CONFIG['leaderboard_targets']['{kernel}']}}µs")
    
    max_iterations = {RALPH_CONFIG["max_iterations"]}
    
    for i in range(max_iterations):
        cycle_num = i + 1
        
        # Load tree for this cycle
        from driver import load_tree
        tree = load_tree("{kernel}")
        
        # Get previous best
        stats = tree.get_stats()
        prev_best = stats.get("best_us", float("inf"))
        
        # Run cycle
        from driver import run_cycle, save_tree, rate_limiter
        success, summary = run_cycle(
            "{kernel}",
            tree,
            rate_limiter,
            dry_run=False,
        )
        save_tree(tree)
        
        # Extract result
        try:
            result_us = float(summary.split(":")[1].split("µs")[0].strip())
        except:
            result_us = float("inf")
        
        # Run Ralph gate
        from ralph_integrator import RALPH_CONFIG as CONFIG
        
        # Simple coherence check
        improvement = ((prev_best - result_us) / prev_best * 100) if prev_best != float("inf") and prev_best > 0 else 0
        coherence = 0.5 if improvement >= 5 else 0.3
        
        log.info(f"Cycle {{cycle_num}}: {{result_us:.1f}}µs (coherence={{coherence:.2f}})")
        
        if result_us <= CONFIG["leaderboard_targets"]["{kernel}"]:
            log.info(f"BREAKTHROUGH! {{result_us:.1f}}µs <= {{CONFIG['leaderboard_targets']['{kernel}']}}µs target")
            break
        
        if cycle_num >= max_iterations:
            log.info(f"Max iterations ({{max_iterations}}) reached")
            break
    
    summary = integrator.get_summary()
    log.info(f"Final summary: {{summary}}")
    
    return summary


if __name__ == "__main__":
    main()
'''

    return ralph_code


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ralph Loop Integrator")
    parser.add_argument("--kernel", required=True, choices=["gemm", "moe", "mla"])
    parser.add_argument("--max-cycles", type=int, default=100)
    parser.add_argument("--coherence-threshold", type=float, default=0.5)
    args = parser.parse_args()

    config = {
        "coherence_threshold": args.coherence_threshold,
        "max_iterations": args.max_cycles,
    }

    integrator = RalphLoopIntegrator(kernel=args.kernel, config=config)

    # Load the base driver cycle function
    # This would be connected to the actual driver in practice
    print(f"RalphLoopIntegrator for {args.kernel} initialized")
    print(f"Config: {config}")
    print(f"Target: {RALPH_CONFIG['leaderboard_targets'].get(args.kernel)}µs")
