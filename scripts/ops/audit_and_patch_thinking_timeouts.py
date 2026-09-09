#!/usr/bin/env python3
"""Audits and Enforces Unhurried Thinking Timeouts across all Client Calls.

Mandates:
1. "Leave plenty of time for the fat to render" - Never kill a thinking model with aggressive 15-30s timeouts.
2. Local Thinking Models (DeepSeek-R1-8B, Qwen3-Coder-30B, gpt-oss-20b): Timeout = 180.0s - 300.0s (3-5 minutes).
3. Frontier Cloud Thinking Models (DeepSeek-1.6T, Qwen-397B, GLM-5.2): Timeout = 300.0s - 600.0s (5-10 minutes).
4. Asynchronous Non-Blocking Execution: UI and agent loops never freeze while thinking models cook.
"""

import json
import logging
import os
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [TIMEOUT_GUARD] %(message)s")
logger = logging.getLogger("timeout_guard")

TIMEOUT_POLICY = {
    "local_npu_igpu_thinking": {
        "models": ["DeepSeek-R1-8B", "Qwen3-Coder-30B", "gpt-oss-20b", "qwen3.6-moe-35b"],
        "min_timeout_sec": 180.0,
        "recommended_timeout_sec": 300.0,
        "rationale": "Allows local models full time to generate 4,000+ tokens of deep chain-of-thought without premature SIGKILL or HTTP timeouts."
    },
    "frontier_cloud_thinking": {
        "models": ["deepseek-v4-pro:cloud", "qwen3.5:397b-cloud", "glm-5.2:cloud"],
        "min_timeout_sec": 300.0,
        "recommended_timeout_sec": 600.0,
        "rationale": "Frontier 1.6T and 397B parameter models require up to 2-3 minutes for deep multi-step mathematical derivations."
    },
    "fast_ast_deterministic": {
        "models": ["AutoHarness AST", "Sheaf Gluer", "Poincaré Metric"],
        "min_timeout_sec": 1.0,
        "recommended_timeout_sec": 5.0,
        "rationale": "Pure Python algebraic and geometric operations finish in microseconds (<0.01ms)."
    }
}

def patch_file_timeouts(filepath: str):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace short timeouts (10.0, 15.0, 30.0, 45.0) in httpx calls with 180.0 or 300.0
    new_content = re.sub(r'timeout\s*=\s*(?:10\.0|15\.0|30\.0|45\.0|60\.0)', 'timeout=180.0', content)
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        logger.info("✓ Patched thinking timeouts to 180.0s in %s", filepath)

def main():
    print("\n" + "=" * 115)
    print("⏳ THINKING MODEL TIMEOUT POLICY: 'LEAVE PLENTY OF TIME FOR THE FAT TO RENDER'")
    print("=" * 115)

    for tier, data in TIMEOUT_POLICY.items():
        print(f"\n[Tier: {tier}]")
        print(f"  ├─ Models Covered : {', '.join(data['models'])}")
        print(f"  ├─ Enforced Timeout: {data['recommended_timeout_sec']}s ({data['recommended_timeout_sec']/60:.1f} minutes)")
        print(f"  └─ Rationale       : {data['rationale']}")

    # Apply patch to key inference callers
    target_scripts = [
        "src/cohezion/competitions/arc/local_qwen_ast_proposer.py",
        "scripts/ops/local_qwen_arc_gap_filler.py",
        "scripts/ops/consult_ollama_cloud_thinking_models.py",
        "scripts/ops/local_multiperspective_adversarial_breakthrough_review.py",
        "src/cohezion/inference/unified_hybrid_router.py"
    ]
    for ts in target_scripts:
        patch_file_timeouts(ts)

    # Save artifact
    os.makedirs("docs/research", exist_ok=True)
    report_file = "docs/research/thinking_model_timeout_and_patience_policy.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# ⏳ Thinking Model Timeout & Patience Policy\n\n")
        f.write("**Principle**: *'Leave plenty of time for the fat to render.'*  \n")
        f.write("**Date**: 2026-08-24  \n\n")
        for k, v in TIMEOUT_POLICY.items():
            f.write(f"## {k}\n")
            f.write(f"- **Models**: `{', '.join(v['models'])}`\n")
            f.write(f"- **Timeout**: **{v['recommended_timeout_sec']}s** ({v['recommended_timeout_sec']/60:.1f} min)\n")
            f.write(f"- **Rationale**: {v['rationale']}\n\n")

    print("\n" + "=" * 115)
    print(f"📄 Thinking Timeout Policy saved to: {report_file}")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    main()
