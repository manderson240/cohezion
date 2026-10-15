#!/usr/bin/env python3
"""Comprehensive Benchmark of Safe Local NPU Models on AMD XDNA 2.
===================================================================
Tests all verified, zero-UMA-contention NPU models on their distinct
specialized strengths, ensuring we match each model to its optimal
task and avoid its architectural failure modes.
"""

import json
import logging
import time
import urllib.request
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("NPUSafeBenchmark")

PORT = 8005
ENDPOINT = f"http://127.0.0.1:{PORT}/v1/chat/completions"

# Safe NPU Model Roster mapped to specialized tasks
BENCHMARK_SUITE = [
    {
        "model_id": "deepseek-r1-0528:8b",
        "display_name": "DeepSeek-R1-0528-8B",
        "category": "Mathematical & Formal Reasoning",
        "specialized_task": "ARC-AGI-2 Dihedral Group Proof",
        "prompt": (
            "Prove why a 2D integer grid transformed by the Dihedral group D4 (8 symmetries) "
            "preserves topological Euler characteristics. Provide a concise, rigorous mathematical proof."
        ),
        "max_tokens": 256,
        "temperature": 0.1,
        "target_strength": "Deep step-by-step chain-of-thought (<think>) and abstract algebra rigor.",
        "weakness_to_avoid": "Do not use for fast low-latency UI reflex or raw speed triage.",
    },
    {
        "model_id": "qwen3.5:4b",
        "display_name": "Qwen3.5-4B",
        "category": "DSL & Function Code Synthesis",
        "specialized_task": "ARC-AGI Python DSL Candidate Generator",
        "prompt": (
            "Write a clean, deterministic Python function `reflect_vertical(grid: list[list[int]]) -> list[list[int]]` "
            "with zero external dependencies and strict type annotations."
        ),
        "max_tokens": 128,
        "temperature": 0.1,
        "target_strength": "Syntactically flawless Python code generation with exact AST signatures.",
        "weakness_to_avoid": "Do not use for non-code subjective philosophy or open-ended speculation.",
    },
    {
        "model_id": "gemma3:4b",
        "display_name": "Gemma3-4B",
        "category": "Biomedical & Structured Taxonomy",
        "specialized_task": "RSNA Knee Pathology JSON Extraction",
        "prompt": (
            "You are a medical radiology extractor. Output ONLY a valid JSON object extracting: "
            "pathology: 'ACL Tear', severity: 'Grade 3', compartment: 'Lateral', confidence: 0.94."
        ),
        "max_tokens": 100,
        "temperature": 0.1,
        "target_strength": "Strict schema conformity, medical/scientific terminology extraction.",
        "weakness_to_avoid": "Do not query without explicit JSON constraints to avoid token repetition.",
    },
    {
        "model_id": "gemma4-it:e2b",
        "display_name": "Gemma4-E2B-IT",
        "category": "High-Speed Instruction & Invariant Classification",
        "specialized_task": "NFL BDB Kinematic Invariant Classifier",
        "prompt": (
            "Classify the following physical metric: closing acceleration a = 1.29 yd/s^2 before contact. "
            "Is this a conserved kinematic quantity under time translation symmetry? Answer YES or NO with 1 justification sentence."
        ),
        "max_tokens": 80,
        "temperature": 0.1,
        "target_strength": "Rapid instruction compliance, fast zero-shot binary/ternary classification.",
        "weakness_to_avoid": "Do not use for multi-file AST refactoring or large-context synthesis.",
    },
    {
        "model_id": "llama3.2:1b",
        "display_name": "Llama-3.2-1B",
        "category": "Ultra-Low Latency Reflex & Syntax Triage",
        "specialized_task": "Sub-50ms Candidate Invariant Triage",
        "prompt": "Evaluate candidate token: 'd4_rot90'. Output ONLY the domain: 'ARC_AGI' or 'OTHER'.",
        "max_tokens": 20,
        "temperature": 0.0,
        "target_strength": "Sub-100ms response time, zero-allocation gatekeeper / reflex router.",
        "weakness_to_avoid": "Never use for complex logic, multi-step math, or AST code transformations.",
    },
]


def query_model(item: Dict[str, Any]) -> Dict[str, Any]:
    payload = json.dumps({
        "model": item["model_id"],
        "messages": [{"role": "user", "content": item["prompt"]}],
        "max_tokens": item["max_tokens"],
        "temperature": item["temperature"],
    }).encode("utf-8")

    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latency_sec = time.perf_counter() - t0
            choices = data.get("choices", [])
            msg = choices[0].get("message", {}) if choices else {}
            content = msg.get("content", "").strip()
            reasoning = msg.get("reasoning_content", "").strip()
            usage = data.get("usage", {})
            return {
                "success": True,
                "latency_sec": latency_sec,
                "content": content,
                "reasoning": reasoning,
                "usage": usage,
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "latency_sec": time.perf_counter() - t0,
        }


def main():
    logger.info("==================================================================")
    logger.info("STARTING SAFE NPU MULTI-MODEL SPECIALIZATION BENCHMARK SUITE")
    logger.info("==================================================================")

    results = []
    for item in BENCHMARK_SUITE:
        logger.info("\n--- Benchmarking Model: %s (%s) ---", item["display_name"], item["category"])
        logger.info("Specialized Task: %s", item["specialized_task"])
        logger.info("Target Strength:  %s", item["target_strength"])
        logger.info("Weakness to Avoid: %s", item["weakness_to_avoid"])

        res = query_model(item)
        if res["success"]:
            usage = res["usage"]
            logger.info("✓ SUCCESS in %.2fs!", res["latency_sec"])
            logger.info("  Load Duration:    %.2fs", usage.get("load_duration", 0.0))
            logger.info("  Prefill TTFT:     %.2fs (%.1f TPS)", usage.get("prefill_duration_ttft", 0.0), usage.get("prefill_speed_tps", 0.0))
            logger.info("  Decoding Speed:   %.1f TPS", usage.get("decoding_speed_tps", 0.0))
            logger.info("  Tokens Generated: %d", usage.get("completion_tokens", 0))
            if res["reasoning"]:
                logger.info("  Reasoning Snippet: %s", res["reasoning"][:150].replace("\n", " "))
            logger.info("  Output Snippet:    %s", res["content"][:200].replace("\n", " "))
        else:
            logger.error("✗ FAILED: %s", res.get("error"))

        results.append({**item, **res})
        time.sleep(2.0)

    # Summary
    logger.info("\n==================================================================")
    logger.info("BENCHMARK SUMMARY & SPECIALIZATION ROSTER")
    logger.info("==================================================================")
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        tps = r.get("usage", {}).get("decoding_speed_tps", 0.0)
        logger.info("%-20s | %-6s | %5.1f TPS | %s", r["display_name"], status, tps, r["specialized_task"])

    # Save to JSON
    out_file = "/tmp/safe_npu_benchmark_results.json"
    with open(out_file, "w") as fp:
        json.dump(results, fp, indent=2)
    logger.info("\nDetailed results saved to %s", out_file)


if __name__ == "__main__":
    main()
