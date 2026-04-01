#!/usr/bin/env python3
"""
Benchmark on Reference Problems (with ground truth)

Measures baseline accuracy before applying breakthrough components.
"""

import re

import polars as pl


def extract_numbers(text):
    return [int(x) for x in re.findall(r'\d+', text)]


def solve_baseline(problem_text):
    """Simple baseline solver."""
    text = problem_text.lower()
    
    # Zero patterns
    if "1-1" in text or "0*" in text or "*0" in text:
        return 0
    
    # Equation patterns
    match = re.search(r'=\s*(\d+)', text)
    if match:
        return int(match.group(1)) % 100000
    
    # Last number fallback
    numbers = extract_numbers(problem_text)
    if numbers:
        return numbers[-1] % 100000
    
    return 0


def run_benchmark(reference_csv="input/reference.csv"):
    """Run benchmark on reference problems."""
    ref_df = pl.read_csv(reference_csv)
    
    print(f"{'='*60}")
    print(f"AIMO Baseline Benchmark")
    print(f"{'='*60}")
    print(f"Problems: {len(ref_df)}")
    print(f"{'='*60}\n")
    
    correct = 0
    results = []
    
    for idx in range(len(ref_df)):
        problem_id = ref_df[idx, "id"]
        problem_text = ref_df[idx, "problem"]
        expected = ref_df[idx, "answer"]
        
        answer = solve_baseline(problem_text)
        is_correct = (answer == expected)
        
        if is_correct:
            correct += 1
        
        status = "✅" if is_correct else "❌"
        print(f"{status} {problem_id}: Expected={expected}, Got={answer}")
        
        results.append({
            "id": problem_id,
            "expected": expected,
            "actual": answer,
            "correct": is_correct,
        })
    
    accuracy = correct / len(ref_df) if len(ref_df) > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"Baseline Results")
    print(f"{'='*60}")
    print(f"Accuracy: {accuracy*100:.1f}% ({correct}/{len(ref_df)})")
    print(f"{'='*60}")
    
    return {
        "total": len(ref_df),
        "correct": correct,
        "accuracy": accuracy,
        "results": results,
    }


if __name__ == "__main__":
    results = run_benchmark()
