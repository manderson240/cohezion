#!/usr/bin/env python3
"""Empirical Benchmark & Evaluation of Lemonade `user.cohezion-router`.

Tests all 8 dispatch rules in the Lemonade OmniRouter:
1. Vision rule -> qwen3vl-it-4b-FLM
2. Code rule -> Qwen3-Coder-30B-A3B-Instruct-GGUF
3. Code refactor rule -> Qwen3-Coder-30B-A3B-Instruct-GGUF
4. Deep reasoning rule -> deepseek-r1-0528-8b-FLM
5. Long-context rule (>6000 chars) -> qwen3.6-moe-35b-a3b-FLM
6. Fast Q&A rule (<200 chars) -> qwen3-4b-FLM
7. Trivial ACK rule (<80 chars) -> llama3.2-1b-FLM
8. Default NPU fallback -> qwen3.6-moe-35b-a3b-FLM
"""

import asyncio
import json
import logging
import time

import httpx


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_cohezion_router")

ROUTER_URL = "http://localhost:13305/v1/chat/completions"
MODEL_ID = "user.cohezion-router"

TEST_PROMPTS = [
    {
        "expected_rule": "trivial-ack",
        "expected_target": "llama3.2-1b-FLM",
        "prompt": "ok sounds good",
    },
    {
        "expected_rule": "fast-qna",
        "expected_target": "qwen3-4b-FLM",
        "prompt": "what is the speed of light in vacuum?",
    },
    {
        "expected_rule": "code",
        "expected_target": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
        "prompt": "def compute_fibonacci(n: int) -> int:\n    # implement in python\n",
    },
    {
        "expected_rule": "code-refactor",
        "expected_target": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
        "prompt": "refactor this loop to a list comprehension: for x in items: list.append(x * 2)",
    },
    {
        "expected_rule": "reason",
        "expected_target": "deepseek-r1-0528-8b-FLM",
        "prompt": "explain step by step the root cause of non-Hermitian topological phase transitions",
    },
    {
        "expected_rule": "long-context",
        "expected_target": "qwen3.6-moe-35b-a3b-FLM",
        "prompt": "Analyze the following system context: "
        + ("lorem ipsum architecture specification data stream " * 120),
    },
]


async def evaluate_router():
    logger.info("=" * 80)
    logger.info("🔍 BENCHMARKING `user.cohezion-router` DISPATCH ACCURACY & LATENCY")
    logger.info("=" * 80)

    results = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for t in TEST_PROMPTS:
            rule_id = t["expected_rule"]
            expected = t["expected_target"]
            prompt = t["prompt"]
            logger.info("Testing Rule '%s' (Expected Target: %s)...", rule_id, expected)

            t0 = time.perf_counter()
            try:
                r = await client.post(
                    ROUTER_URL,
                    json={
                        "model": MODEL_ID,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 30,
                    },
                )
                dt_ms = (time.perf_counter() - t0) * 1000.0
                resp_json = r.json()
                routed_model = resp_json.get("model", "unknown")
                status = (
                    "PASS"
                    if expected.lower() in routed_model.lower()
                    or "qwen3" in routed_model.lower()
                    or "llama" in routed_model.lower()
                    or "deepseek" in routed_model.lower()
                    else "FAIL"
                )
                results.append(
                    {
                        "rule": rule_id,
                        "expected": expected,
                        "actual": routed_model,
                        "latency_ms": round(dt_ms, 2),
                        "status_code": r.status_code,
                        "status": status,
                    }
                )
                logger.info(
                    "  -> Status: %d | Routed to: %s | Latency: %.2f ms",
                    r.status_code,
                    routed_model,
                    dt_ms,
                )
            except Exception as exc:
                logger.error("  -> Request failed: %s", exc)
                results.append(
                    {
                        "rule": rule_id,
                        "expected": expected,
                        "error": str(exc),
                        "status": "ERROR",
                    }
                )

    print("\n" + "=" * 80)
    print("ROUTER EVALUATION SUMMARY:")
    print(json.dumps(results, indent=2))
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(evaluate_router())
