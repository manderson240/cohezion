"""Benchmark local Lemonade models through the OmniRouter on port 13305.

This module compares throughput (tokens per second) across Lemonade lanes
(CPU, iGPU, NPU) using the OpenAI-compatible /v1/chat/completions endpoint.
All local inference routes through port 13305; the legacy direct Ollama path
has been removed to unify health, cost, and quality gating under the fleet.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from typing import Any

import requests


logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = os.environ.get("LEMONADE_BASE_URL", "http://localhost:13305")
DEFAULT_CHAT_PATH = os.environ.get("LEMONADE_CHAT_PATH", "/v1/chat/completions")
DEFAULT_MODELS_PATH = os.environ.get("LEMONADE_MODELS_PATH", "/v1/models")

DEFAULT_PROMPTS = [
    "Explain quantum computing in one sentence.",
    "Write a haiku about machine learning.",
    "What is 2+2?",
]

DEFAULT_MODELS = [
    ("phi4:latest", "CPU"),
    ("Gemma-4-E4B-it-GGUF", "iGPU"),
    ("DeepSeek-Qwen3-8B-FLM", "NPU"),
]


def _post_json(base_url: str, path: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    """POST JSON to Lemonade and return the parsed response."""
    url = f"{base_url}{path}"
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _list_models(base_url: str, models_path: str, timeout: float = 5.0) -> list[str]:
    """Return the list of model IDs currently registered with Lemonade."""
    url = f"{base_url}{models_path}"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("Could not list models from %s: %s", url, exc)
        return []

    models = data.get("data", []) if isinstance(data, dict) else data
    return [m["id"] for m in models if isinstance(m, dict) and "id" in m]


def benchmark_model(
    model: str,
    prompt: str,
    base_url: str = DEFAULT_BASE_URL,
    chat_path: str = DEFAULT_CHAT_PATH,
    system: str = "You are a concise assistant.",
    max_tokens: int = 128,
    timeout: float = 120.0,
) -> tuple[int, float, dict[str, Any]]:
    """Benchmark a single model/prompt pair.

    Returns ``(tokens, elapsed_seconds, raw_response_body)``.
    """
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": False,
    }

    start = time.time()
    data = _post_json(base_url, chat_path, payload, timeout)
    elapsed = time.time() - start
    tokens = data.get("usage", {}).get("total_tokens", 0)
    return tokens, elapsed, data


def run_benchmark(
    models: list[tuple[str, str]] | None = None,
    prompts: list[str] | None = None,
    base_url: str = DEFAULT_BASE_URL,
    chat_path: str = DEFAULT_CHAT_PATH,
    models_path: str = DEFAULT_MODELS_PATH,
    max_tokens: int = 128,
) -> dict[str, Any]:
    """Run a throughput benchmark across configured local models.

    Args:
        models: List of ``(model_id, lane_label)`` tuples. If None, uses
            ``DEFAULT_MODELS``.
        prompts: List of prompts. If None, uses ``DEFAULT_PROMPTS``.
        base_url: Lemonade OmniRouter base URL.
        chat_path: OpenAI-compatible chat endpoint path.
        models_path: OpenAI-compatible models endpoint path.
        max_tokens: Maximum tokens to generate per prompt.

    Returns:
        A structured results dict with per-model and aggregate TPS metrics.
    """
    models = models or DEFAULT_MODELS
    prompts = prompts or DEFAULT_PROMPTS

    available = set(_list_models(base_url, models_path))
    logger.info("Available Lemonade models: %s", sorted(available))

    results: dict[str, Any] = {
        "base_url": base_url,
        "prompts": prompts,
        "max_tokens": max_tokens,
        "models": [],
    }

    for model, lane in models:
        if available and model not in available:
            logger.warning("Skipping %s (%s): not available on Lemonade", model, lane)
            continue

        total_tokens = 0
        total_time = 0.0
        per_prompt: list[dict[str, Any]] = []

        for prompt in prompts:
            try:
                tokens, elapsed, _raw = benchmark_model(
                    model, prompt, base_url, chat_path, max_tokens=max_tokens
                )
            except requests.RequestException as exc:
                logger.warning("Benchmark failed for %s on %r: %s", model, prompt, exc)
                per_prompt.append({"prompt": prompt, "error": str(exc)})
                continue

            tps = tokens / elapsed if elapsed > 0 else 0.0
            total_tokens += tokens
            total_time += elapsed
            per_prompt.append(
                {
                    "prompt": prompt[:40],
                    "tokens": tokens,
                    "elapsed": round(elapsed, 2),
                    "tps": round(tps, 1),
                }
            )

        avg_tps = total_tokens / total_time if total_time > 0 else 0.0
        results["models"].append(
            {
                "model": model,
                "lane": lane,
                "available": bool(available),
                "total_tokens": total_tokens,
                "total_time": round(total_time, 2),
                "average_tps": round(avg_tps, 1),
                "prompts": per_prompt,
            }
        )
        print(f"=== {model} ({lane}) | Avg TPS: {avg_tps:.1f} ===")
        for entry in per_prompt:
            if "error" in entry:
                print(f"  {entry['prompt']:40s} | ERROR: {entry['error']}")
            else:
                print(
                    f"  {entry['prompt']:40s} | "
                    f"Tokens: {entry['tokens']:3d} | "
                    f"Time: {entry['elapsed']:.2f}s | "
                    f"TPS: {entry['tps']:.1f}"
                )
        print(f"METRIC inference_tps_model={model} tps={avg_tps:.1f}")

    return results


def main() -> None:
    """CLI entry point for local Lemonade benchmarking."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Benchmark local Lemonade models on port 13305"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Lemonade OmniRouter base URL (default: http://localhost:13305)",
    )
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Model ID to benchmark; may be given multiple times (default: built-in list)",
    )
    parser.add_argument(
        "--lane",
        action="append",
        dest="lanes",
        help="Lane label for each --model; must match order of --model",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=128,
        help="Maximum tokens to generate per prompt (default: 128)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON results to stdout instead of human-readable summary",
    )
    args = parser.parse_args()

    if args.models and args.lanes and len(args.models) != len(args.lanes):
        parser.error("--model and --lane must be given the same number of times")

    if args.models:
        models = list(zip(args.models, args.lanes or (["unknown"] * len(args.models))))
    else:
        models = None

    results = run_benchmark(
        models=models,
        base_url=args.base_url,
        max_tokens=args.max_tokens,
    )

    if args.json:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
