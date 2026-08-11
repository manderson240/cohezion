#!/usr/bin/env python3
"""
NPU MoE Capability Elicitation Script (qwen3.6-moe-35b-a3b-FLM)
================================================================
Elicits latent reasoning, 12D hyperbolic tensor physics, and self-verifying
code-as-action synthesis from the 35B NPU MoE model on AMD XDNA2.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "elicitations"


def elicit_npu(prompt: str, system_prompt: str = "", max_tokens: int = 1500) -> dict:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "qwen3.6-moe-35b-a3b-FLM",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    req = urllib.request.Request(
        LEMONADE_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            res = json.loads(r.read().decode())
            dt = round(time.time() - t0, 2)
            msg = res["choices"][0]["message"]
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning_content") or ""
            return {
                "success": True,
                "duration_s": dt,
                "content": content.strip(),
                "reasoning": reasoning.strip(),
                "total_chars": len(content) + len(reasoning),
            }
    except Exception as e:
        return {"success": False, "error": str(e), "duration_s": round(time.time() - t0, 2)}


def main():
    print("=== Eliciting Latent Capabilities from qwen3.6-moe-35b-a3b-FLM (NPU MoE) ===")

    elicitations = {}

    # Test 1: 12D Parallel Transport & Riemannian Curvature Tensor Elicitation
    print("\n[1/3] Eliciting 12D Poincaré Parallel Transport & Metric Tensor...")
    p1 = (
        "You are an expert theoretical physicist and differential geometer.\n"
        "Derive the exact Christoffel symbols \\Gamma^k_{ij} for the 12D Poincaré ball metric tensor "
        "g_{ij}(x) = \\frac{4}{(1 - ||x||^2)^2} \\delta_{ij}.\n"
        "Then write a complete, pure-Python function `parallel_transport_12d(v_start, x_start, x_end)` "
        "that transports a 12D vector along a geodesic."
    )
    sys1 = "You think in J-Space latent vectors before outputting code. Show complete reasoning in <think> tags."
    elicitations["12d_tensor_physics"] = elicit_npu(p1, system_prompt=sys1)
    print(f"  ✓ Pass 1 finished in {elicitations['12d_tensor_physics']['duration_s']}s (Chars: {elicitations['12d_tensor_physics'].get('total_chars', 0)})")

    # Test 2: Zero-Cost AutoHarness AST Loop-Safety Prover
    print("\n[2/3] Eliciting Static AST Infinite Loop & Halting Prover...")
    p2 = (
        "Write a Python AST transformer `class LoopSafetyProver(ast.NodeVisitor)` that statically proves "
        "whether a Python function's `while` loops have guaranteed monotonic termination expressions.\n"
        "Include non-trivial test cases."
    )
    sys2 = "You are a compiler verification architect. Enforce deterministic static analysis."
    elicitations["ast_loop_prover"] = elicit_npu(p2, system_prompt=sys2)
    print(f"  ✓ Pass 2 finished in {elicitations['ast_loop_prover']['duration_s']}s (Chars: {elicitations['ast_loop_prover'].get('total_chars', 0)})")

    # Test 3: AdS/CFT Holographic J-Space Bulk-to-Boundary Reconstruction
    print("\n[3/3] Eliciting Holographic J-Space Bulk Reconstruction Kernel...")
    p3 = (
        "Formulate a mathematical operator `HolographicMapper` that maps continuous 256-dim J-Space "
        "z-vectors onto a 12D boundary CFT embedding space, preserving FLUME 0.5 HIHO coherence.\n"
        "Provide Python implementation code."
    )
    sys3 = "You operate at the intersection of quantum information theory and modern AI architectures."
    elicitations["holographic_jspace"] = elicit_npu(p3, system_prompt=sys3)
    print(f"  ✓ Pass 3 finished in {elicitations['holographic_jspace']['duration_s']}s (Chars: {elicitations['holographic_jspace'].get('total_chars', 0)})")

    # Persist report to Vault
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = VAULT_DIR / "NPU_MOE_ELICITED_CAPABILITIES.md"

    md_lines = [
        "# Elicited Capabilities — qwen3.6-moe-35b-a3b-FLM (AMD XDNA2 NPU MoE)",
        "*Date: 2026-08-03*",
        "*Hardware: AMD Strix Halo XDNA2 NPU (`recipe: flm`, `pinned: true`)*\n",
    ]

    for key, data in elicitations.items():
        md_lines.append(f"## Capability: {key.upper()}")
        md_lines.append(f"- **Success**: {data.get('success')}")
        md_lines.append(f"- **Latency**: {data.get('duration_s')}s")
        md_lines.append(f"- **Output Length**: {data.get('total_chars')} characters\n")

        if data.get("reasoning"):
            md_lines.append("### Reasoning (<think>):")
            md_lines.append(f"```\n{data['reasoning']}\n```\n")

        if data.get("content"):
            md_lines.append("### Output Code / Synthesis:")
            md_lines.append(f"```python\n{data['content']}\n```\n")
        elif data.get("error"):
            md_lines.append(f"### Error:\n`{data['error']}`\n")

    report_file.write_text("\n".join(md_lines))
    print(f"\n✅ Elicitation report written to Vault: {report_file}")


if __name__ == "__main__":
    main()
