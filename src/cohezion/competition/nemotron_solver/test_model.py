"""Test Gemma-4 on Nemotron hard problem types."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "orchestrator"))
from model_dispatcher import ModelDispatcher


SYSTEM = "You are a puzzle-solving expert. Given examples showing a secret transformation rule, infer the rule and apply it to solve the final puzzle. Be concise. Output ONLY the answer with no explanation."


def test_problems(problems: list[dict]):
    dispatcher = ModelDispatcher()
    correct = 0
    for r in problems:
        result = dispatcher.generate(
            SYSTEM,
            r["prompt"],
            max_tokens=64,
            temperature=0.0,
        )
        pred = result.text.strip()
        # Clean up: remove quotes, spaces, etc.
        pred = pred.strip('"').strip("'").strip()
        ans = r["answer"].strip()
        ok = pred == ans
        correct += ok
        print(f"{'✓' if ok else '✗'} Pred: {pred:30s} | Ans: {ans:30s} | {r['prompt'][:60]}...")
    print(f"\nAccuracy: {correct}/{len(problems)} = {correct / len(problems) * 100:.1f}%")


if __name__ == "__main__":
    with open("/tmp/train.csv") as f:
        rows = list(csv.DictReader(f))

    # Sample 5 of each type
    types = ["bit_manip", "equations", "encryption"]
    for ptype in types:
        check = {
            "bit_manip": lambda p: "bit manipulation" in p.lower(),
            "equations": lambda p: "equation" in p.lower() or "transformation rules" in p.lower(),
            "encryption": lambda p: "encryption" in p.lower(),
        }[ptype]
        samples = [r for r in rows if check(r["prompt"])][:5]
        print(f"\n=== {ptype.upper()} (5 samples) ===")
        test_problems(samples)
