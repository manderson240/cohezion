#!/usr/bin/env python3
"""
AutoHarness Benchmark - Context Engineering + Quality Optimization

Tests that context engineering and autoharness improve both throughput AND quality.
"""

import asyncio
import sys
import time

import aiohttp


sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

from cohezion.inference.context_engineering import (
    AutoHarness,
    ContextEngineer,
    QualityMonitor,
    create_autoharness,
)


async def test_model_with_harness(
    model_id: str,
    harness: AutoHarness,
    test_tasks: list[dict],
    base_url: str = "http://localhost:8002",
) -> dict:
    """Test a model with the autoharness."""

    monitor = QualityMonitor()
    results = []

    async with aiohttp.ClientSession() as session:
        for task in test_tasks:
            # Get optimized payload from autoharness
            payload = harness.get_optimized_payload(
                user_prompt=task["prompt"],
                task_type=task["type"],
                complexity=task["complexity"],
                quality_priority=task.get("quality_priority", 0.5),
            )

            start = time.time()
            try:
                async with session.post(
                    f"{base_url}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    data = await resp.json()
                    elapsed = (time.time() - start) * 1000

                    text = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("completion_tokens", 0)

                    # Quality assessment
                    quality = monitor.assess(text, task_type=task["type"])

                    results.append(
                        {
                            "task": task["type"],
                            "tokens": tokens,
                            "latency_ms": elapsed,
                            "tps": tokens / (elapsed / 1000) if elapsed > 0 else 0,
                            "quality": quality,
                            "text_preview": text[:100] + "..." if len(text) > 100 else text,
                        }
                    )

                    # Provide feedback to harness
                    harness.feedback(
                        {"params": payload, "latency_ms": elapsed, "tokens": tokens}, quality
                    )

            except Exception as e:
                results.append({"task": task["type"], "error": str(e)})

    # Aggregate results
    valid = [r for r in results if "error" not in r]
    if valid:
        avg_quality = sum(r["quality"]["overall"] for r in valid) / len(valid)
        avg_tps = sum(r["tps"] for r in valid) / len(valid)
        avg_latency = sum(r["latency_ms"] for r in valid) / len(valid)
    else:
        avg_quality = avg_tps = avg_latency = 0

    return {
        "model": model_id,
        "tasks_completed": len(valid),
        "avg_quality": avg_quality,
        "avg_tps": avg_tps,
        "avg_latency_ms": avg_latency,
        "results": valid,
    }


async def test_baseline_vs_harness():
    """Compare baseline settings vs autoharness optimization."""

    print("=" * 70)
    print("AUTOHARNESS BENCHMARK: Baseline vs Context-Engineered")
    print("=" * 70)

    # Discover actual model
    base_url = "http://localhost:8002"
    async with aiohttp.ClientSession() as session, session.get(f"{base_url}/v1/models") as resp:
        data = await resp.json()
        models = [m["id"] for m in data.get("data", [])]
        model_id = models[0] if models else "unknown"
        print(f"\nModel detected: {model_id}\n")

    test_tasks = [
        {
            "prompt": "Write a Python function to calculate fibonacci numbers.",
            "type": "coding",
            "complexity": "medium",
            "quality_priority": 0.7,
        },
        {
            "prompt": "Explain why the sky is blue.",
            "type": "reasoning",
            "complexity": "medium",
            "quality_priority": 0.6,
        },
        {
            "prompt": "What are 3 benefits of exercise?",
            "type": "default",
            "complexity": "low",
            "quality_priority": 0.4,
        },
        {
            "prompt": "Solve: If 5 workers build a house in 12 days, how long for 8 workers?",
            "type": "reasoning",
            "complexity": "high",
            "quality_priority": 0.8,
        },
    ]

    # Test 1: Baseline (generic settings)
    print("-" * 70)
    print("TEST 1: BASELINE (Generic Settings)")
    print("-" * 70)

    engineer = ContextEngineer()
    baseline_harness = AutoHarness(model_id, engineer=engineer)

    # Force baseline by using low quality priority
    baseline_results = await test_model_with_harness(model_id, baseline_harness, test_tasks)

    print(f"Avg TPS: {baseline_results['avg_tps']:.1f}")
    print(f"Avg Quality: {baseline_results['avg_quality']:.2f}/1.0")
    print(f"Avg Latency: {baseline_results['avg_latency_ms']:.0f}ms")

    # Test 2: Context-engineered (model-specific)
    print("\n" + "-" * 70)
    print("TEST 2: CONTEXT-ENGINEERED (Model-Specific)")
    print("-" * 70)

    autoharness = create_autoharness(model_id)

    # Run twice - first to learn, second to apply
    print("Learning phase...")
    await test_model_with_harness(model_id, autoharness, test_tasks)

    print("Optimized phase...")
    harnessed_results = await test_model_with_harness(model_id, autoharness, test_tasks)

    print(f"Avg TPS: {harnessed_results['avg_tps']:.1f}")
    print(f"Avg Quality: {harnessed_results['avg_quality']:.2f}/1.0")
    print(f"Avg Latency: {harnessed_results['avg_latency_ms']:.0f}ms")

    # Comparison
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)

    tps_change = (
        (
            (harnessed_results["avg_tps"] - baseline_results["avg_tps"])
            / baseline_results["avg_tps"]
            * 100
        )
        if baseline_results["avg_tps"] > 0
        else 0
    )
    quality_change = (
        (
            (harnessed_results["avg_quality"] - baseline_results["avg_quality"])
            / baseline_results["avg_quality"]
            * 100
        )
        if baseline_results["avg_quality"] > 0
        else 0
    )

    print(f"{'Metric':<20} {'Baseline':<15} {'Harnessed':<15} {'Change':<15}")
    print("-" * 70)
    print(
        f"{'TPS':<20} {baseline_results['avg_tps']:<15.1f} {harnessed_results['avg_tps']:<15.1f} {tps_change:>+14.1f}%"
    )
    print(
        f"{'Quality':<20} {baseline_results['avg_quality']:<15.2f} {harnessed_results['avg_quality']:<15.2f} {quality_change:>+14.1f}%"
    )
    print(
        f"{'Latency (ms)':<20} {baseline_results['avg_latency_ms']:<15.0f} {harnessed_results['avg_latency_ms']:<15.0f} "
        f"{((harnessed_results['avg_latency_ms'] - baseline_results['avg_latency_ms']) / baseline_results['avg_latency_ms'] * 100):>+13.1f}%"
    )

    # Conclusion
    print("\n" + "=" * 70)
    if harnessed_results["avg_quality"] >= baseline_results["avg_quality"]:
        print("✓ Context engineering MAINTAINS or IMPROVES quality")
    else:
        print("⚠ Quality degradation detected")

    if abs(tps_change) < 10:
        print("✓ Throughput impact within acceptable range (<10%)")
    elif tps_change > 0:
        print(f"✓ Throughput IMPROVED by {tps_change:.1f}%")
    else:
        print(f"⚠ Throughput decreased by {abs(tps_change):.1f}%")
    print("=" * 70)

    # Show learned params
    print("\nLearned optimal parameters:")
    for key, params in autoharness._optimal_params.items():
        print(f"  {key}: {params}")

    # Sample outputs
    print("\n" + "=" * 70)
    print("SAMPLE OUTPUTS")
    print("=" * 70)
    for r in harnessed_results["results"][:2]:
        print(f"\nTask: {r['task']}")
        print(f"Quality: {r['quality']['overall']:.2f} | TPS: {r['tps']:.1f}")
        print(f"Output: {r['text_preview']}")

    print(f"\nMETRIC baseline_tps={baseline_results['avg_tps']:.1f}")
    print(f"METRIC harnessed_tps={harnessed_results['avg_tps']:.1f}")
    print(f"METRIC baseline_quality={baseline_results['avg_quality']:.2f}")
    print(f"METRIC harnessed_quality={harnessed_results['avg_quality']:.2f}")
    print(
        f"METRIC quality_preserved={1 if harnessed_results['avg_quality'] >= baseline_results['avg_quality'] * 0.9 else 0}"
    )


if __name__ == "__main__":
    asyncio.run(test_baseline_vs_harness())
