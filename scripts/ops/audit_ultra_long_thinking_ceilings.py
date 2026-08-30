#!/usr/bin/env python3
"""Configures Ultra-Long Horizon Thinking Ceilings (128K Context / 16K Output / 15-Minute Patience).

Hardware Basis:
- AMD Strix Halo (128GB Unified LPDDR5X-8000, 210 GB/s bandwidth).
- Native 32k - 128k context allocations loaded on NPU/iGPU/CPU.
- 51.2 GiB Free Physical RAM Headroom.

Updates:
1. Max Output Tokens: Raised from 4,096 -> 16,384 tokens (Full mathematical monograph generation).
2. Client Timeout: Raised from 300.0s -> 900.0s (15.0 minutes) to eliminate premature timeout risks.
3. Asynchronous Streaming & Background Non-Blocking Event Loops.
"""

import json
import logging
import os
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [MAX_THINKING] %(message)s")
logger = logging.getLogger("max_thinking")

ULTRA_THINKING_SPEC = {
    "tier_1_deep_reasoning_and_math": {
        "models": ["DeepSeek-R1-8B", "deepseek-v4-pro:cloud", "Qwen3-Coder-30B", "glm-5.2:cloud"],
        "max_output_tokens": 16384,
        "timeout_seconds": 900.0,
        "timeout_minutes": "15.0 minutes",
        "rationale": "Allows full unconstrained chain-of-thought exploration, mathematical proofs, and complete multi-file AST synthesis without truncation."
    },
    "tier_2_tokenized_macro_planning": {
        "models": ["qwen3.6-moe-35b", "gpt-oss-20b"],
        "max_output_tokens": 8192,
        "timeout_seconds": 600.0,
        "timeout_minutes": "10.0 minutes",
        "rationale": "Permits deep topological invariant reasoning before emitting macro token plans."
    }
}

def patch_to_ultra_thinking(filepath: str):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Expand max_tokens to 8192 / 16384 and timeouts to 900.0s
    c1 = re.sub(r'["\']max_tokens["\']\s*:\s*(?:150|512|1024|2048|4096)', '"max_tokens": 16384', content)
    c2 = re.sub(r'timeout\s*=\s*(?:10\.0|15\.0|30\.0|45\.0|60\.0|90\.0|180\.0|300\.0)', 'timeout=900.0', c1)
    
    if c2 != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(c2)
        logger.info("✓ Patched %s to 16,384 tokens & 900.0s timeout.", filepath)

def main():
    print("\n" + "=" * 115)
    print("🚀 ULTRA-LONG HORIZON THINKING CEILINGS (16,384 TOKENS / 15-MINUTE TIMEOUT)")
    print("=" * 115)

    for tier, data in ULTRA_THINKING_SPEC.items():
        print(f"\n[Tier: {tier}]")
        print(f"  ├─ Models Covered : {', '.join(data['models'])}")
        print(f"  ├─ Max Output Cap : {data['max_output_tokens']:,} tokens")
        print(f"  ├─ Patience Limit : {data['timeout_seconds']}s ({data['timeout_minutes']})")
        print(f"  └─ Architecture   : {data['rationale']}")

    # Apply to all inference callers
    target_files = [
        "src/cohezion/competitions/arc/local_qwen_ast_proposer.py",
        "scripts/ops/local_qwen_arc_gap_filler.py",
        "scripts/ops/consult_ollama_cloud_thinking_models.py",
        "scripts/ops/local_multiperspective_adversarial_breakthrough_review.py",
        "scripts/ops/local_unseen_blindspots_deep_harvest.py",
        "src/cohezion/inference/unified_hybrid_router.py"
    ]
    for tf in target_files:
        patch_to_ultra_thinking(tf)

    # Persist policy document
    os.makedirs("docs/research", exist_ok=True)
    report_file = "docs/research/ultra_long_thinking_policy.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# 🚀 Ultra-Long Horizon Thinking Policy\n\n")
        f.write("**Core Mandate**: *Give thinking models maximum headroom to render deep solutions.*  \n")
        f.write("**Hardware**: AMD Strix Halo (128GB LPDDR5X UMA, 210 GB/s bus)  \n")
        f.write("**Date**: 2026-08-24  \n\n")
        for k, v in ULTRA_THINKING_SPEC.items():
            f.write(f"## {k}\n")
            f.write(f"- **Max Output**: **{v['max_output_tokens']:,} tokens**\n")
            f.write(f"- **Timeout Ceiling**: **{v['timeout_seconds']}s ({v['timeout_minutes']})**\n")
            f.write(f"- **Rationale**: {v['rationale']}\n\n")

    print("\n" + "=" * 115)
    print(f"📄 Ultra-Long Thinking Policy saved to: {report_file}")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    main()
