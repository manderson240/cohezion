#!/usr/bin/env python3
"""Kaggle-compatible inference server for AIMO3.

Uses standard Kaggle evaluation templates.
"""

import os
import sys


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Kaggle evaluation infrastructure
sys.path.insert(0, "/kaggle/input/ai-mathematical-olympiad-progress-prize-3")
import re

import polars as pl
import requests
from kaggle_evaluation.core.templates import InferenceServer


class AIMO3InferenceServer(InferenceServer):
    """
    Inference server for AIMO3 competition.

    Uses Ollama for reasoning and returns integer answers.
    """

    MODEL = "qwen3-coder:30b"
    OLLAMA_URL = "http://localhost:11434/api/generate"
    TIMEOUT = 300  # seconds per problem

    def predict(self, data_batch: pl.DataFrame, transforms=None) -> pl.DataFrame:
        """
        Process a batch of problems and return answers.

        Args:
            data_batch: DataFrame with 'id' and 'problem' columns

        Returns:
            DataFrame with 'id' and 'answer' columns
        """
        results = []

        for row in data_batch.iter_rows(named=True):
            problem_id = row["id"]
            problem_text = row["problem"]

            # Solve the problem
            answer = self._solve(problem_text)

            results.append({"id": problem_id, "answer": answer})

        return pl.DataFrame(results)

    def _solve(self, problem_text: str) -> int:
        """Solve a single problem using Ollama."""

        prompt = f"""Solve this mathematical olympiad problem step-by-step.

Problem: {problem_text}

Provide your reasoning, then give the final answer as a single integer in this format:

FINAL ANSWER: <integer>"""

        try:
            response = requests.post(
                self.OLLAMA_URL,
                json={
                    "model": self.MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 4096,
                    },
                },
                timeout=self.TIMEOUT,
            )

            if response.status_code != 200:
                return 0

            result = response.json()
            text = result.get("response", "")

            # Extract answer
            return self._extract_answer(text)

        except Exception:
            return 0

    def _extract_answer(self, text: str) -> int:
        """Extract integer from response."""
        # Look for FINAL ANSWER
        match = re.search(r"FINAL ANSWER:\s*(-?\d+)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Fallback: last number in response
        numbers = re.findall(r"-?\d+", text)
        if numbers:
            return int(numbers[-1])

        return 0


# Kaggle entry point
if __name__ == "__main__":
    if os.getenv("KAGGLE_IS_COMPETITION_RERUN"):
        # Production mode
        import aimo_3_gateway

        gateway = aimo_3_gateway.AIMO3Gateway()
        gateway.run()
    else:
        print("Run with KAGGLE_IS_COMPETITION_RERUN=1 for evaluation")
        print("Or use simple_solver.py for local testing")
