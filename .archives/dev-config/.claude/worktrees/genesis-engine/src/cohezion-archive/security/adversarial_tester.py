"""
Adversarial Security Tester - High-Performance Testing Framework.

Runs millions of adversarial tests against security components:
- PromptGuard (prompt injection detection)
- Validators (SQL, XSS, path traversal, command injection)
- OutputFilter (PII, toxic content)

Features:
- Parallel execution with ProcessPoolExecutor
- Progress tracking with ETA
- Memory-efficient streaming
- Comprehensive metrics collection
- CSV/JSON export
"""

import csv
import json
import logging
import multiprocessing
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cohezion.security.attack_patterns import (
    PATTERN_SUMMARY,
    AttackPattern,
    generate_test_batch,
    get_pattern_count,
)
from cohezion.security.prompt_guard import PromptGuard, ThreatLevel
from cohezion.security.validators import ValidationResult, validate_input


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single adversarial test."""

    pattern: str
    category: str
    subcategory: str
    expected_blocked: bool
    actually_blocked: bool
    detection_method: str  # prompt_guard, validator, output_filter
    threat_level: str
    processing_time_ms: float
    correct: bool = field(init=False)

    def __post_init__(self):
        self.correct = self.expected_blocked == self.actually_blocked


@dataclass
class TestMetrics:
    """Aggregated test metrics."""

    total_tests: int = 0
    correct_detections: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    total_time_ms: float = 0.0
    by_category: dict = field(default_factory=lambda: defaultdict(lambda: {"total": 0, "correct": 0, "fp": 0, "fn": 0}))

    @property
    def detection_rate(self) -> float:
        """True positive rate."""
        actual_attacks = self.total_tests - self.false_positives
        if actual_attacks == 0:
            return 0.0
        return (actual_attacks - self.false_negatives) / actual_attacks

    @property
    def false_positive_rate(self) -> float:
        """False positive rate."""
        if self.total_tests == 0:
            return 0.0
        return self.false_positives / self.total_tests

    @property
    def accuracy(self) -> float:
        """Overall accuracy."""
        if self.total_tests == 0:
            return 0.0
        return self.correct_detections / self.total_tests

    @property
    def avg_processing_time_ms(self) -> float:
        """Average processing time per test."""
        if self.total_tests == 0:
            return 0.0
        return self.total_time_ms / self.total_tests

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "total_tests": self.total_tests,
            "correct_detections": self.correct_detections,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "detection_rate": f"{self.detection_rate:.4%}",
            "false_positive_rate": f"{self.false_positive_rate:.4%}",
            "accuracy": f"{self.accuracy:.4%}",
            "avg_processing_time_ms": f"{self.avg_processing_time_ms:.2f}",
            "total_time_seconds": f"{self.total_time_ms / 1000:.2f}",
            "by_category": dict(self.by_category),
        }


def test_single_pattern(pattern: AttackPattern) -> TestResult:
    """
    Test a single attack pattern against security components.

    Args:
        pattern: Attack pattern to test

    Returns:
        TestResult with detection outcome
    """
    start_time = time.perf_counter()

    # Initialize components
    guard = PromptGuard(strict_mode=True)

    # Test prompt guard first
    prompt_analysis = guard.analyze(pattern.pattern)
    prompt_blocked = prompt_analysis.threat_level in (
        ThreatLevel.SUSPICIOUS,
        ThreatLevel.MALICIOUS,
    )

    # Test validator
    validation_result = validate_input(pattern.pattern)
    validator_blocked = validation_result is not None and validation_result.code == ValidationResult.BLOCKED_PATTERN

    # Combined result
    actually_blocked = prompt_blocked or validator_blocked

    # Determine which method detected
    if prompt_blocked and validator_blocked:
        detection_method = "both"
    elif prompt_blocked:
        detection_method = "prompt_guard"
    elif validator_blocked:
        detection_method = "validator"
    else:
        detection_method = "none"

    end_time = time.perf_counter()
    processing_time_ms = (end_time - start_time) * 1000

    return TestResult(
        pattern=pattern.pattern[:100],  # Truncate for storage
        category=pattern.category.value,
        subcategory=pattern.subcategory,
        expected_blocked=pattern.expected_blocked,
        actually_blocked=actually_blocked,
        detection_method=detection_method,
        threat_level=prompt_analysis.threat_level.value,
        processing_time_ms=processing_time_ms,
    )


def run_test_batch(patterns: list[AttackPattern]) -> list[TestResult]:
    """Run a batch of tests (for parallel execution)."""
    return [test_single_pattern(p) for p in patterns]


class AdversarialTester:
    """High-performance adversarial security tester."""

    def __init__(
        self,
        output_dir: str | Path = "results",
        workers: int | None = None,
        batch_size: int = 1000,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workers = workers or max(1, multiprocessing.cpu_count() - 2)
        self.batch_size = batch_size
        self.metrics = TestMetrics()
        self.failed_patterns: list[TestResult] = []
        self.start_time: float | None = None

    def run(
        self,
        rounds: int = 1_000_000,
        benign_ratio: float = 0.05,
        save_failures: bool = True,
    ) -> TestMetrics:
        """
        Run adversarial tests.

        Args:
            rounds: Number of test rounds
            benign_ratio: Ratio of benign patterns for false positive testing
            save_failures: Whether to save failed test cases

        Returns:
            Aggregated test metrics
        """
        self.start_time = time.time()
        logger.info(f"Starting adversarial testing: {rounds:,} rounds")
        logger.info(f"Workers: {self.workers}, Batch size: {self.batch_size}")
        logger.info(f"Pattern database: {get_pattern_count()} base patterns")

        # Generate test batches
        total_batches = (rounds + self.batch_size - 1) // self.batch_size
        processed = 0

        with ProcessPoolExecutor(max_workers=self.workers) as executor:
            futures = []

            # Submit batches
            for batch_idx in range(total_batches):
                batch_rounds = min(self.batch_size, rounds - processed)
                patterns = list(generate_test_batch(batch_rounds, benign_ratio))
                future = executor.submit(run_test_batch, patterns)
                futures.append((batch_idx, future))
                processed += batch_rounds

            # Process results as they complete
            completed = 0
            for batch_idx, future in futures:
                try:
                    results = future.result(timeout=300)  # 5 min timeout
                    self._process_results(results)
                    completed += 1

                    # Progress logging every 10 batches
                    if completed % 10 == 0:
                        self._log_progress(completed, total_batches)

                except Exception as e:
                    logger.error(f"Batch {batch_idx} failed: {e}")

        # Final summary
        elapsed = time.time() - self.start_time
        logger.info(f"Completed {self.metrics.total_tests:,} tests in {elapsed:.1f}s")
        logger.info(f"Detection rate: {self.metrics.detection_rate:.4%}")
        logger.info(f"False positive rate: {self.metrics.false_positive_rate:.4%}")
        logger.info(f"Accuracy: {self.metrics.accuracy:.4%}")

        # Save results
        self._save_results(save_failures)

        return self.metrics

    def _process_results(self, results: list[TestResult]) -> None:
        """Process a batch of test results."""
        for result in results:
            self.metrics.total_tests += 1
            self.metrics.total_time_ms += result.processing_time_ms

            if result.correct:
                self.metrics.correct_detections += 1
            elif result.expected_blocked and not result.actually_blocked:
                self.metrics.false_negatives += 1
                self.failed_patterns.append(result)
            else:  # Not expected blocked but was blocked
                self.metrics.false_positives += 1
                self.failed_patterns.append(result)

            # By category tracking
            cat = result.category
            self.metrics.by_category[cat]["total"] += 1
            if result.correct:
                self.metrics.by_category[cat]["correct"] += 1
            elif result.expected_blocked and not result.actually_blocked:
                self.metrics.by_category[cat]["fn"] += 1
            else:
                self.metrics.by_category[cat]["fp"] += 1

    def _log_progress(self, completed: int, total: int) -> None:
        """Log progress with ETA."""
        elapsed = time.time() - self.start_time
        rate = self.metrics.total_tests / elapsed if elapsed > 0 else 0
        remaining = total - completed
        eta_seconds = (remaining * self.batch_size) / rate if rate > 0 else 0
        eta = timedelta(seconds=int(eta_seconds))

        logger.info(
            f"Progress: {completed}/{total} batches | "
            f"{self.metrics.total_tests:,} tests | "
            f"{rate:.0f} tests/sec | "
            f"ETA: {eta}"
        )

    def _save_results(self, save_failures: bool) -> None:
        """Save test results to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save metrics JSON
        metrics_path = self.output_dir / f"adversarial_metrics_{timestamp}.json"
        with open(metrics_path, "w") as f:
            json.dump(self.metrics.to_dict(), f, indent=2, default=str)
        logger.info(f"Saved metrics to {metrics_path}")

        # Save failures CSV
        if save_failures and self.failed_patterns:
            failures_path = self.output_dir / f"adversarial_failures_{timestamp}.csv"
            with open(failures_path, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "pattern",
                        "category",
                        "subcategory",
                        "expected_blocked",
                        "actually_blocked",
                        "detection_method",
                        "threat_level",
                        "processing_time_ms",
                        "correct",
                    ],
                )
                writer.writeheader()
                for result in self.failed_patterns[:10000]:  # Cap at 10K
                    writer.writerow(
                        {
                            "pattern": result.pattern,
                            "category": result.category,
                            "subcategory": result.subcategory,
                            "expected_blocked": result.expected_blocked,
                            "actually_blocked": result.actually_blocked,
                            "detection_method": result.detection_method,
                            "threat_level": result.threat_level,
                            "processing_time_ms": f"{result.processing_time_ms:.2f}",
                            "correct": result.correct,
                        }
                    )
            logger.info(f"Saved {len(self.failed_patterns)} failures to {failures_path}")

        # Generate report
        self._generate_report(timestamp)

    def _generate_report(self, timestamp: str) -> None:
        """Generate markdown security report."""
        report_path = self.output_dir / f"adversarial_report_{timestamp}.md"

        elapsed = time.time() - self.start_time

        report = f"""# Adversarial Security Testing Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Duration:** {elapsed:.1f} seconds

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {self.metrics.total_tests:,} |
| Correct Detections | {self.metrics.correct_detections:,} |
| False Positives | {self.metrics.false_positives:,} |
| False Negatives | {self.metrics.false_negatives:,} |
| Detection Rate | {self.metrics.detection_rate:.4%} |
| False Positive Rate | {self.metrics.false_positive_rate:.4%} |
| Overall Accuracy | {self.metrics.accuracy:.4%} |
| Avg Processing Time | {self.metrics.avg_processing_time_ms:.2f}ms |

## Results by Category

| Category | Total | Correct | FP | FN | Accuracy |
|----------|-------|---------|----|----|----------|
"""
        for cat, stats in sorted(self.metrics.by_category.items()):
            acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            report += (
                f"| {cat} | {stats['total']:,} | {stats['correct']:,} | {stats['fp']} | {stats['fn']} | {acc:.2%} |\n"
            )

        report += f"""
## Attack Pattern Coverage

- **Base Patterns:** {get_pattern_count()}
- **Pattern Categories:** {len(PATTERN_SUMMARY["by_category"])}
- **Mutations Applied:** Yes (10x expansion)

## Recommendations

"""
        # Add recommendations based on results
        if self.metrics.false_negatives > 0:
            report += f"- ⚠️ **{self.metrics.false_negatives} attacks bypassed detection** - Review failed patterns and enhance rules\n"

        if self.metrics.false_positives > 0:
            report += f"- ⚠️ **{self.metrics.false_positives} false positives** - Adjust detection thresholds\n"

        if self.metrics.detection_rate >= 0.999:
            report += "- ✅ **Detection rate ≥99.9%** - Security posture is strong\n"
        elif self.metrics.detection_rate >= 0.99:
            report += "- 🟡 **Detection rate ≥99%** - Good but room for improvement\n"
        else:
            report += "- ❌ **Detection rate <99%** - Immediate hardening required\n"

        report += f"""
## Files Generated

- `adversarial_metrics_{timestamp}.json` - Detailed metrics
- `adversarial_failures_{timestamp}.csv` - Failed test cases
- `adversarial_report_{timestamp}.md` - This report

---

*Generated by Cohezion Adversarial Security Tester*
"""
        with open(report_path, "w") as f:
            f.write(report)
        logger.info(f"Saved report to {report_path}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Adversarial Security Testing Framework")
    parser.add_argument(
        "--rounds",
        "-r",
        type=int,
        default=10000,
        help="Number of test rounds (default: 10000)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="results",
        help="Output directory (default: results)",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=None,
        help="Number of parallel workers (default: CPU count - 2)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=1000,
        help="Batch size for parallel processing (default: 1000)",
    )
    parser.add_argument(
        "--benign-ratio",
        type=float,
        default=0.05,
        help="Ratio of benign patterns for false positive testing (default: 0.05)",
    )

    args = parser.parse_args()

    tester = AdversarialTester(
        output_dir=args.output,
        workers=args.workers,
        batch_size=args.batch_size,
    )

    metrics = tester.run(
        rounds=args.rounds,
        benign_ratio=args.benign_ratio,
    )

    # Exit with error if detection rate is too low
    if metrics.detection_rate < 0.99:
        logger.error(f"Detection rate {metrics.detection_rate:.4%} below 99% threshold")
        sys.exit(1)

    logger.info("Adversarial testing completed successfully")


if __name__ == "__main__":
    main()
