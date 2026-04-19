#!/usr/bin/env python3
"""Quick validation with cloud models before full benchmark."""

import time

from base_specialist import BaseSpecialist


TEST_PROBLEMS = [
    ("test_1", "What is 1-1?", 0),
    ("test_2", "What is 0×10?", 0),
    ("test_3", "Solve 4+x=4 for x", 0),
]


def main():
    print("=" * 60)
    print("QUICK CLOUD VALIDATION")
    print("=" * 60)
    print(f"Model: qwen3.5:cloud")
    print(f"Testing {len(TEST_PROBLEMS)} trivial problems...\n")

    # Use cloud model for fast validation
    specialist = BaseSpecialist("Algebraist", model_name="qwen3.5:cloud", timeout=600)

    results = []
    for problem_id, problem, expected in TEST_PROBLEMS:
        print(f"Solving: {problem_id} - {problem[:50]}...")
        t0 = time.time()
        result = specialist.solve(problem)
        elapsed = time.time() - t0

        answer = specialist.extract_answer(result)
        status = "✓" if answer == expected else "✗"

        print(f"  {status} Time: {elapsed:.1f}s, Answer: {answer}, Expected: {expected}")
        print(f"  Raw: {result[:80]}...\n")

        results.append(
            {
                "id": problem_id,
                "correct": answer == expected,
                "time": elapsed,
                "answer": answer,
            }
        )

    # Summary
    correct = sum(1 for r in results if r["correct"])
    total = len(results)
    avg_time = sum(r["time"] for r in results) / total

    print("=" * 60)
    print(f"SUMMARY: {correct}/{total} correct ({correct / total * 100:.0f}%)")
    print(f"Average time: {avg_time:.1f}s/problem")
    print(f"Total time: {sum(r['time'] for r in results):.1f}s")
    print("=" * 60)

    if correct == total:
        print("✅ All tests passed - ready for full benchmark")
        return 0
    else:
        print("❌ Some tests failed - check answer extraction")
        return 1


if __name__ == "__main__":
    exit(main())
