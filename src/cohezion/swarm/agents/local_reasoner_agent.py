"""
Local Reasoner Benchmark - Evaluates Ollama models on logic tasks.
"""

import asyncio
import json
import logging
import time
from typing import Any

from cohezion.swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class LocalReasonerAgent(BaseAgent):
    """
    Agent for benchmarking local model reasoning.
    """

    async def process(self, input_data: str) -> str:
        """
        Main entry point for processing reasoning tasks.
        """
        result = await self.benchmark_task(self.model_name, input_data)
        return result.get("response", "Reasoning failed.")

    async def benchmark_task(self, model: str, task: str) -> dict[str, Any]:
        """
        Runs a specific reasoning task and returns the result with metrics.
        """
        self.model_name = model

        start_time = time.perf_counter()
        try:
            response = await self._call_ollama(task)
            duration = time.perf_counter() - start_time

            # Simplified score extraction (in future, use EthicsAgent or similar as judge)
            return {
                "model": model,
                "response": response,
                "duration_sec": duration,
                "success": len(response) > 50,  # Basic heuristic
            }
        except Exception as e:
            return {"model": model, "error": str(e), "success": False}


async def main():
    agent = LocalReasonerAgent(model_name="deepseek-r1:70b")
    tasks = [
        "Explain the concept of HIHO stability in 12D physics.",
        "Solve the following logic puzzle: If a thought vector has a velocity of 0.5 in the x-dimension and a momentum of 0.9, where will it be in 3 steps assuming constant force?",
        "Write a Python function to perform semantic arithmetic (z1 + z2 - z3) using numpy.",
    ]

    models = ["mistral:7b", "gemma3:4b", "qwen3-coder:30b"]
    results = []

    for model in models:
        print(f"Benchmarking Model: {model}")
        for task in tasks:
            print(f"Running Task: {task[:50]}...")
            res = await agent.benchmark_task(model, task)
            results.append(res)

    # Save results
    with open("local_reasoner_benchmark.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Benchmark complete. Results saved to local_reasoner_benchmark.json")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
