#!/usr/bin/env python3
"""
breakthrough_tracker.py - Systematic learning capture for Rank 1 breakthroughs

Captures:
- Every experiment attempted
- What worked vs what failed
- Current hypotheses
- Next highest-leverage experiments
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Directories
WORKTREE = Path("/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint")
LEARNINGS_DIR = Path("/tmp/luma_learnings")
LEARNINGS_DIR.mkdir(exist_ok=True)

DB_FILE = LEARNINGS_DIR / "breakthrough_db.json"
LOG_FILE = LEARNINGS_DIR / "experiments.jsonl"


class BreakthroughTracker:
    """Track experiments and learnings systematically."""

    def __init__(self):
        self.db = self.load_db()

    def load_db(self) -> Dict:
        """Load or create learning database."""
        if DB_FILE.exists():
            with open(DB_FILE) as f:
                return json.load(f)
        return {
            "kernels": {
                "mla": {
                    "baseline_us": 69.7,
                    "best_us": None,
                    "target_us": 26.0,
                    "experiments": [],
                    "hypotheses": [],
                    "patterns_learned": [],
                },
                "moe": {
                    "baseline_us": 93.4,
                    "best_us": 93.4,
                    "target_us": 70.47,
                    "experiments": [],
                    "hypotheses": [],
                    "patterns_learned": [],
                },
                "gemm": {
                    "baseline_us": 13.0,
                    "best_us": None,
                    "target_us": 4.327,
                    "experiments": [],
                    "hypotheses": [],
                    "patterns_learned": [],
                },
            },
            "meta": {"created": datetime.now().isoformat(), "version": "1.0"},
        }

    def save_db(self):
        """Save database."""
        with open(DB_FILE, "w") as f:
            json.dump(self.db, f, indent=2)

    def log_experiment(
        self,
        kernel: str,
        variant: str,
        old_time: float,
        new_time: Optional[float],
        success: bool,
        notes: str,
    ):
        """Log an experiment with full context."""

        experiment = {
            "timestamp": datetime.now().isoformat(),
            "kernel": kernel,
            "variant": variant,
            "old_time_us": old_time,
            "new_time_us": new_time,
            "improvement_pct": ((old_time - new_time) / old_time * 100) if new_time else None,
            "success": success,
            "notes": notes,
        }

        self.db["kernels"][kernel]["experiments"].append(experiment)

        # Log to JSONL for easy processing
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(experiment) + "\n")

        # Update best if improved
        if (
            success
            and new_time
            and (
                not self.db["kernels"][kernel]["best_us"]
                or new_time < self.db["kernels"][kernel]["best_us"]
            )
        ):
            self.db["kernels"][kernel]["best_us"] = new_time
            print(f"🎉 NEW BEST for {kernel}: {new_time:.2f}µs")

        self.save_db()

    def add_hypothesis(
        self,
        kernel: str,
        name: str,
        description: str,
        expected_improvement: float,
        confidence: str = "medium",
    ):
        """Add new hypothesis to test."""

        hypothesis = {
            "id": len(self.db["kernels"][kernel]["hypotheses"]) + 1,
            "name": name,
            "description": description,
            "expected_improvement_pct": expected_improvement,
            "confidence": confidence,
            "status": "pending",
            "created": datetime.now().isoformat(),
        }

        self.db["kernels"][kernel]["hypotheses"].append(hypothesis)
        self.save_db()

        print(f"🧠 Added hypothesis for {kernel}: {name}")
        return hypothesis["id"]

    def update_hypothesis_status(self, kernel: str, hid: int, status: str, results: str):
        """Update hypothesis status with results."""

        for h in self.db["kernels"][kernel]["hypotheses"]:
            if h["id"] == hid:
                h["status"] = status
                h["results"] = results
                h["completed"] = datetime.now().isoformat()
                break

        self.save_db()

    def get_breakthrough_candidates(self) -> List[Dict]:
        """Return experiments most likely to yield breakthroughs."""

        candidates = []

        for kernel, data in self.db["kernels"].items():
            current = data.get("best_us") or data["baseline_us"]
            target = data["target_us"]
            gap = current - target

            # Sort hypotheses by expected improvement
            pending = [h for h in data["hypotheses"] if h["status"] == "pending"]
            pending.sort(key=lambda x: x["expected_improvement_pct"], reverse=True)

            candidates.append(
                {
                    "kernel": kernel,
                    "current_us": current,
                    "target_us": target,
                    "gap_us": gap,
                    "gap_pct": (gap / current * 100),
                    "top_hypothesis": pending[0] if pending else None,
                    "pending_count": len(pending),
                }
            )

        # Sort by gap (smallest first = closest to target)
        candidates.sort(key=lambda x: x["gap_us"])

        return candidates

    def generate_breakthrough_plan(self) -> str:
        """Generate actionable breakthrough plan."""

        candidates = self.get_breakthrough_candidates()

        report = []
        report.append("=" * 60)
        report.append("🎯 BREAKTHROUGH RESEARCH PLAN")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        report.append("")

        for c in candidates:
            report.append(f"\n[{c['kernel'].upper()}]")
            report.append(f"  Current: {c['current_us']:.2f}µs")
            report.append(f"  Target:  {c['target_us']:.2f}µs")
            report.append(f"  Gap:     {c['gap_us']:.2f}µs ({c['gap_pct']:.1f}% remaining)")
            report.append(
                f"  Priority: {'🔥 HIGH' if c['gap_pct'] < 50 else 'MEDIUM' if c['gap_pct'] < 100 else 'LOW'}"
            )

            if c["top_hypothesis"]:
                h = c["top_hypothesis"]
                report.append(f"  Top Hypothesis:")
                report.append(f"    #{h['id']}: {h['name']}")
                report.append(f"    Expected: +{h['expected_improvement_pct']:.1f}% improvement")
                report.append(f"    Confidence: {h['confidence']}")

            report.append(f"  Pending: {c['pending_count']} hypotheses")

        report.append("\n" + "=" * 60)
        report.append("RECOMMENDED NEXT STEPS:")
        report.append("=" * 60)

        top = candidates[0]
        report.append(f"1. Focus on {top['kernel'].upper()} (closest to Rank 1)")
        if top["top_hypothesis"]:
            report.append(f"2. Test: {top['top_hypothesis']['name']}")
        report.append(f"3. Target: Reduce {top['gap_us']:.2f}µs gap")

        return "\n".join(report)

    def discover_patterns(self):
        """Analyze experiments to discover patterns."""

        patterns = []

        for kernel, data in self.db["kernels"].items():
            experiments = data["experiments"]

            if len(experiments) >= 3:
                # Find what succeeds
                successes = [e for e in experiments if e["success"]]
                failures = [e for e in experiments if not e["success"]]

                if successes and failures:
                    # Look for patterns
                    success_variants = set(e["variant"] for e in successes)
                    failure_variants = set(e["variant"] for e in failures)

                    pattern = f"{kernel}: {len(successes)} successes, {len(failures)} failures"
                    patterns.append(pattern)

        return patterns

    def display_summary(self):
        """Display current status summary."""

        print("\n" + "=" * 60)
        print("📚 LEARNING DATABASE SUMMARY")
        print("=" * 60)

        for kernel, data in self.db["kernels"].items():
            print(f"\n[{kernel.upper()}]")
            print(f"  Baseline: {data['baseline_us']:.2f}µs")
            print(f"  Best:     {data['best_us']:.2f}µs" if data["best_us"] else "  Best:     None")
            print(f"  Target:   {data['target_us']:.2f}µs")
            print(f"  Experiments: {len(data['experiments'])}")
            print(
                f"  Hypotheses:  {len(data['hypotheses'])} ({len([h for h in data['hypotheses'] if h['status'] == 'pending'])} pending)"
            )

        print("\n" + "=" * 60)


def main():
    """Main learning capture system."""

    tracker = BreakthroughTracker()

    # Display current status
    tracker.display_summary()

    # Get breakthrough plan
    plan = tracker.generate_breakthrough_plan()
    print(plan)

    # Save plan
    plan_file = LEARNINGS_DIR / "breakthrough_plan.txt"
    with open(plan_file, "w") as f:
        f.write(plan)

    print(f"\n✅ Plan saved to: {plan_file}")


if __name__ == "__main__":
    main()
