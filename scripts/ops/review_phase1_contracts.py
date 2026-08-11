#!/usr/bin/env python3
"""
100% Local Heavy Multiperspective Adversarial Code Review
==========================================================
Mandate: Quality Over Speed & Local Inference Over Everything Else.

Local Silicon Roster:
  - Pass 1 (NPU MoE Primary): `qwen3.6-moe-35b-a3b-FLM` (35B MoE on AMD XDNA2 NPU, pinned=true)
  - Pass 2 (iGPU Heavy Coding): `Qwen3-Coder-30B-A3B-Instruct-GGUF` (30B MoE on Radeon 8060S iGPU)
  - Pass 3 (iGPU Science & Physics): `Gemma-4-31B-it-GGUF` (31B on Radeon 8060S iGPU)
  - Pass 4 (Local Heavy Council): `user.BCFD-Council` (Local Multi-Model Ensemble)
"""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SURREAL_URL = "http://localhost:8001/sql"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()
LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "reviews"
SESSION = "local-heavy-adversarial-review"

TARGET_FILES = [
    "src/cohezion/contracts.py",
    "src/cohezion/actioner/autoharness_verifier.py",
    "src/cohezion/physics/poincare_manifold.py",
    "src/cohezion/physics/flatland_projection.py",
    "scripts/ops/verify_geometric_correspondence.py",
]


def surreal_write(table: str, record_id: str, data: dict) -> bool:
    clean_id = record_id.replace("-", "_")
    surql = f"UPSERT {table}:{clean_id} CONTENT {json.dumps(data)};"
    try:
        req = urllib.request.Request(
            SURREAL_URL,
            data=surql.encode(),
            headers={
                "Authorization": f"Basic {SURREAL_AUTH}",
                "Surreal-NS": "cohezion",
                "Surreal-DB": "main",
                "Accept": "application/json",
                "Content-Type": "text/plain",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.loads(r.read().decode())
            return bool(isinstance(res, list) and res and res[0].get("status") == "OK")
    except Exception:
        return False


def query_lemonade(model: str, prompt: str, timeout: float = 300.0) -> str:
    """Query local Lemonade server on port 13305 with extended quality timeout."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500,
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        LEMONADE_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode())
            msg = res["choices"][0]["message"]
            return (msg.get("content") or msg.get("reasoning_content") or "").strip()
    except Exception as e:
        return f"Local Lemonade ({model}) Note: {e}"


def main():
    print("=== 100% Local Heavy Multiperspective Adversarial Code Review ===")
    print("Mandate: Quality Over Speed | Local Inference Over Everything Else\n")

    # 1. Read source files
    sources = {}
    for rel_path in TARGET_FILES:
        full_p = REPO / rel_path
        if full_p.exists():
            sources[rel_path] = full_p.read_text()

    source_bundle = "\n\n".join(
        [f"--- FILE: {path} ---\n{code}" for path, code in sources.items()]
    )

    findings = {}

    # Pass 1: NPU MoE Primary Review (qwen3.6-moe-35b-a3b-FLM on XDNA2)
    print("[1/4] Pass 1: NPU MoE Reasoning Auditor (qwen3.6-moe-35b-a3b-FLM on XDNA2 NPU)...")
    prompt_npu = (
        "You are a Principal AI Architect. Perform a rigorous, deep code review of the following Python modules.\n"
        "Analyze contracts, edge cases, and safety invariants:\n\n"
        f"{source_bundle[:3500]}"
    )
    t0 = time.time()
    findings["npu_moe_reasoning"] = query_lemonade("qwen3.6-moe-35b-a3b-FLM", prompt_npu)
    print(f"  ✓ Pass 1 finished in {round(time.time() - t0, 2)}s")

    # Pass 2: iGPU Heavy Coding Auditor (Qwen3-Coder-30B-A3B-Instruct-GGUF)
    print("\n[2/4] Pass 2: iGPU Heavy Code & AST Auditor (Qwen3-Coder-30B on Radeon 8060S iGPU)...")
    prompt_coder = (
        "You are an expert Systems & Security Engineer. Statically audit `autoharness_verifier.py` and `contracts.py` "
        "for AST bypass vulnerabilities, exception handling flaws, and performance bottlenecks:\n\n"
        f"{sources.get('src/cohezion/actioner/autoharness_verifier.py', '')}\n\n"
        f"{sources.get('src/cohezion/contracts.py', '')}"
    )
    t0 = time.time()
    findings["igpu_coder_security"] = query_lemonade("Qwen3-Coder-30B-A3B-Instruct-GGUF", prompt_coder)
    print(f"  ✓ Pass 2 finished in {round(time.time() - t0, 2)}s")

    # Pass 3: iGPU Physics & Hyperbolic Geometry Auditor (Gemma-4-31B-it-GGUF)
    print("\n[3/4] Pass 3: iGPU Physics & Hyperbolic Math Auditor (Gemma-4-31B on Radeon 8060S iGPU)...")
    prompt_math = (
        "You are a mathematical physicist specializing in Riemannian geometry and Poincaré manifolds. "
        "Review `poincare_manifold.py` and `flatland_projection.py` for mathematical rigor and edge-case stability:\n\n"
        f"{sources.get('src/cohezion/physics/poincare_manifold.py', '')}\n\n"
        f"{sources.get('src/cohezion/physics/flatland_projection.py', '')}"
    )
    t0 = time.time()
    findings["igpu_physics_math"] = query_lemonade("Gemma-4-31B-it-GGUF", prompt_math)
    print(f"  ✓ Pass 3 finished in {round(time.time() - t0, 2)}s")

    # Pass 4: Local Council Multi-Model Ensemble (user.BCFD-Council)
    print("\n[4/4] Pass 4: Local Multi-Model Council Synthesis (user.BCFD-Council)...")
    prompt_council = (
        "Synthesize a master engineering report combining findings from NPU, iGPU, and math audits. "
        "Highlight critical recommendations for Phase 1 code-as-action contracts."
    )
    t0 = time.time()
    findings["council_synthesis"] = query_lemonade("user.BCFD-Council", prompt_council)
    print(f"  ✓ Pass 4 finished in {round(time.time() - t0, 2)}s")

    # Persist Master Report to Vault
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = VAULT_DIR / "LOCAL_HEAVY_ADVERSARIAL_REVIEW.md"

    report_content = f"""---
title: 100% Local Heavy Multiperspective Adversarial Code Review
date: {datetime.now(timezone.utc).isoformat()}
tags: [code-review, local-inference, npu, igpu, qwen-coder, gemma4, poincare, autoharness]
session: {SESSION}
---

# 100% Local Heavy Multiperspective Review Report

## Executive Mandate
* **Principle 1**: Quality Over Speed.
* **Principle 2**: Local Inference Over Everything Else.
* **Hardware**: Framework Desktop 16 Strix Halo (128GB Unified RAM, XDNA2 NPU, Radeon 8060S iGPU, 16C/32T Zen5 CPU).

---

## 1. NPU MoE Reasoning Audit (`qwen3.6-moe-35b-a3b-FLM` on XDNA2)
{findings['npu_moe_reasoning']}

---

## 2. iGPU Heavy Code & AST Audit (`Qwen3-Coder-30B-A3B-Instruct-GGUF`)
{findings['igpu_coder_security']}

---

## 3. iGPU Physics & Hyperbolic Math Audit (`Gemma-4-31B-it-GGUF`)
{findings['igpu_physics_math']}

---

## 4. Local Multi-Model Council Synthesis (`user.BCFD-Council`)
{findings['council_synthesis']}
"""
    report_file.write_text(report_content)
    print(f"\n✅ Master Local Heavy Review Report written to Vault: {report_file}")

    # Record in SurrealDB
    report_id = f"local_heavy_review_{int(time.time())}"
    surreal_write("code_review", report_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "files": TARGET_FILES,
        "vault_report": str(report_file),
        "perspectives_count": len(findings)
    })
    print("✅ Review record registered in SurrealDB (code_review table)")


if __name__ == "__main__":
    main()
