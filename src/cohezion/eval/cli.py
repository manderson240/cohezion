"""CLI for benchmark improvement system.

Provides unified interface to run benchmarks with journey tracking,
self-correction, and pattern analysis.
"""

import argparse
import json
import logging

from cohezion.eval.journey_integration import BenchmarkFeedbackLoop
from cohezion.eval.pattern_analyzer import JourneyAttempt, PatternAnalyzer
from cohezion.eval.self_correction import CorrectionConfig, SelfCorrectionLoop


def run_benchmarks(args):
    """Run benchmarks with optional self-correction."""
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(name)s: %(message)s",
    )

    orchestrator = BenchmarkOrchestrator()

    if args.self_correct:
        # Run with self-correction
        config = CorrectionConfig(
            max_attempts=args.max_attempts,
            temperature_increment=0.1,
            timeout=args.timeout,
            selection_strategy="best_phi" if args.track_journey else "first_pass",
        )
        corrector = SelfCorrectionLoop(config)

        # This would run actual benchmarks - using mock for demo
        print("Running benchmarks with self-correction...")
        print(f"Max attempts per problem: {config.max_attempts}")
        print(f"Selection strategy: {config.selection_strategy}")
    else:
        # Run standard benchmarks
        results = orchestrator.compare_models(
            models=[args.model] if args.model else ["qwen2.5-coder:7b"],
            benchmarks=[args.benchmark] if args.benchmark else ["humaneval"],
            limit=args.limit,
        )

        print(json.dumps(results, indent=2))


def analyze_patterns(args):
    """Analyze patterns from benchmark journeys."""
    analyzer = PatternAnalyzer()

    if args.load_results:
        # Load and analyze from file
        with open(args.load_results) as f:
            data = json.load(f)

        # Convert to JourneyAttempt format
        for attempt in data.get("results", []):
            analyzer.record_attempt(
                phi_score=attempt.get("phi_score", 0.5),
                coherence=attempt.get("coherence", 0.5),
                success=attempt.get("status") == "PASS",
                duration=attempt.get("duration", 0),
                tokens=attempt.get("tokens", 0),
            )

    # Generate analysis
    stats = analyzer.get_statistics()
    correlations = analyzer.compute_correlations()
    recommendations = analyzer.generate_recommendations()

    print("\n=== Pattern Analysis ===\n")
    print(f"Total attempts: {stats['total_attempts']}")
    print(f"Success rate: {stats['success_rate']:.1%}")

    if correlations:
        print("\n=== Correlations with Success ===")
        for metric, corr in correlations.items():
            print(f"  {metric}: {corr['correlation']:.3f} (p={corr['p_value']:.3f})")

    if recommendations:
        print("\n=== Recommendations ===")
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"  {i}. {rec['priority']}: {rec['description']}")


def run_e2e(args):
    """Run end-to-end benchmark improvement loop."""
    print("=== COHEZION Benchmark Improvement System ===\n")

    # Initialize components
    feedback = BenchmarkFeedbackLoop()
    analyzer = PatternAnalyzer()

    print("1. Recording journey data (simulated)...")

    # Record mock results with journey tracking
    import random

    models = [args.model] if args.model else ["qwen2.5-coder:7b"]
    benchmark = args.benchmark or "humaneval"

    for i in range(args.limit or 10):
        phi = random.uniform(0.3, 0.8)
        success = random.random() > 0.7

        feedback.record_result(
            benchmark=benchmark,
            task_id=f"HumanEval/{i}",
            model=models[0],
            success=success,
            completion="def solution(): pass",
            duration=random.uniform(10, 60),
        )

        # Also record in analyzer
        attempt = JourneyAttempt(
            task_id=f"HumanEval/{i}",
            benchmark=benchmark,
            model=models[0],
            success=success,
            phi_score=phi,
            coherence=random.uniform(0.3, 0.8),
            journey_12d=[random.uniform(0.3, 0.7) for _ in range(12)],
            completion="def solution(): pass",
            duration=random.uniform(10, 60),
            num_tokens=random.randint(100, 500),
        )
        analyzer.add_attempt(attempt)

    print(f"   Recorded {len(feedback.journey_tracker.journeys)} journeys")

    print("\n2. Analyzing patterns...")
    analysis = analyzer.analyze()
    recommendations = analyzer.generate_recommendations()

    print(f"   Total attempts: {analysis['total_attempts']}")
    print(f"   Success rate: {analysis['success_rate']:.1%}")

    print("\n3. Key Insights from Analysis:")
    if "phi_score" in analysis:
        ps = analysis["phi_score"]
        print(f"   phi_score - successful mean: {ps.get('successful_mean', 0):.3f}")

    print("\n4. Top Recommendations:")
    for i, rec in enumerate(recommendations[:3], 1):
        print(f"   {i}. [{rec.priority}] {rec.description[:60]}...")

    print("\n5. Improvement Suggestions:")
    suggestions = feedback.get_improvement_suggestions()
    for insight in suggestions.get("insights", [])[:2]:
        print(f"   - {insight[:80]}...")

    print("\n=== Complete ===")
    print("\nTo run actual benchmarks:")
    print(
        "  uv run python -m cohezion.eval.cli run --model qwen2.5-coder:7b --benchmark humaneval --self-correct"
    )


def main():
    parser = argparse.ArgumentParser(
        description="COHEZION Benchmark Improvement System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run benchmarks
    run_parser = subparsers.add_parser("run", help="Run benchmarks")
    run_parser.add_argument("--model", help="Model to test")
    run_parser.add_argument("--benchmark", help="Benchmark to run")
    run_parser.add_argument("--limit", type=int, help="Limit problems")
    run_parser.add_argument(
        "--self-correct", action="store_true", help="Use self-correction"
    )
    run_parser.add_argument("--max-attempts", type=int, default=5)
    run_parser.add_argument("--timeout", type=int, default=120)
    run_parser.add_argument("--track-journey", action="store_true")
    run_parser.add_argument("--verbose", "-v", action="store_true")

    # Analyze patterns
    analyze_parser = subparsers.add_parser("analyze", help="Analyze patterns")
    analyze_parser.add_argument("--load-results", help="Load results from file")

    # E2E
    e2e_parser = subparsers.add_parser("e2e", help="End-to-end run")
    e2e_parser.add_argument("--model", help="Model to test")
    e2e_parser.add_argument("--benchmark", help="Benchmark to run")
    e2e_parser.add_argument("--limit", type=int, help="Limit problems")

    args = parser.parse_args()

    if args.command == "run":
        run_benchmarks(args)
    elif args.command == "analyze":
        analyze_patterns(args)
    elif args.command == "e2e":
        run_e2e(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
