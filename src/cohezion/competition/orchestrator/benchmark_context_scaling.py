"""Lemonade context-length TPS scaling benchmark."""
from __future__ import annotations

import time

from cohezion.competition.orchestrator.model_dispatcher import ModelDispatcher


def main():
    dispatcher = ModelDispatcher()

    # Warm up once
    dispatcher.generate("You are helpful.", "Hello.", max_tokens=10)

    # Build prompts of increasing length
    base = "Explain step by step how to solve this puzzle: "
    prompts = [
        ("Short (10 tokens)", base + "What is 2+2?"),
        ("Medium (50 tokens)", base + "A farmer has 17 sheep and all but 9 die. How many are left? Explain your reasoning carefully."),
        ("Long (150 tokens)", base + "In a grid transformation puzzle, each cell is a color from 0-9. The input grid is transformed to an output grid by applying a sequence of operations like rotation, mirroring, color replacement, gravity, and object detection. Given an input grid of size 5x5 with colors [[0,0,0,0,0],[0,1,1,1,0],[0,1,2,1,0],[0,1,1,1,0],[0,0,0,0,0]], what would the output be after applying a 90-degree clockwise rotation followed by a color map that swaps 1 and 2?" * 2),
    ]

    print("=== Lemonade Context Scaling ===")
    for label, prompt in prompts:
        start = time.time()
        result = dispatcher.generate(
            "You are a concise assistant.",
            prompt,
            max_tokens=64,
        )
        elapsed = time.time() - start
        tokens = result.tokens_used
        tps = tokens / elapsed if elapsed > 0 else 0
        print(f"  {label:20s} | Prompt~{len(prompt):4d} chars | Tokens: {tokens:3d} | Time: {elapsed:.2f}s | TPS: {tps:.1f}")

    # Repeated identical prompt test (cache hit)
    print("\n=== Cache/Warm Test ===")
    prompt = "What is the capital of France?"
    for i in range(3):
        start = time.time()
        result = dispatcher.generate("You are a concise assistant.", prompt, max_tokens=32)
        elapsed = time.time() - start
        tokens = result.tokens_used
        tps = tokens / elapsed if elapsed > 0 else 0
        print(f"  Run {i+1} | Tokens: {tokens:3d} | Time: {elapsed:.2f}s | TPS: {tps:.1f}")


if __name__ == "__main__":
    main()
