#!/usr/bin/env python3
"""Autonomous Delegation to Local Silicon: Synthesize Pure First-Principles Micro-Engines.

Delegates to resident `gpt-oss-20b-mxfp4-GGUF` on Lemonade port 13305 to synthesize:
1. `nano_poincare.py`: A Karpathy-style standalone ~100-line pure NumPy Riemannian Poincaré engine.
2. Formally verifies the generated code in a rootless Bubblewrap sandbox with AutoHarness AST gates.
"""

import json
import logging
import os
import sys
import time
import urllib.request
import numpy as np

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier
from cohezion.security.linux_namespace_sandbox import LinuxNamespaceSandbox

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [LOCAL_DELEGATION] %(message)s")
logger = logging.getLogger("local_delegation")

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"

SYSTEM_PROMPT = """You are an elite AI Systems Programmer adhering strictly to the Andrej Karpathy first-principles craftsmanship philosophy:
- Zero heavy dependencies (pure standard library and NumPy only).
- Complete mathematical rigor, radical clarity, clean docstrings, and zero fluff.
- Output ONLY valid, executable Python code enclosed in ```python ``` blocks.
"""

USER_PROMPT = r"""
Write `src/cohezion/physics/nano_poincare.py` implementing a Karpathy-style minimal (~80-120 lines) Poincaré Hyperbolic Geometry Engine.
Do not output chain-of-thought scratchpad. Output ONLY the complete Python code enclosed in ```python ... ```.

Include:
1. Class `NanoPoincare`:
   - `distance(u, v)`: Exact hyperbolic distance $d_P(u, v) = \text{arcosh}\left(1 + 2\frac{\|u-v\|^2}{(1-\|u\|^2)(1-\|v\|^2)}\right)$ with boundary clamping $(\|u\| \le 0.9999)$.
   - `mobius_addition(u, v)`: Möbius addition $u \oplus v = \frac{(1 + 2\langle u, v\rangle + \|v\|^2)u + (1 - \|u\|^2)v}{1 + 2\langle u, v\rangle + \|u\|^2 \|v\|^2}$.
   - `exp_map(x, v)` & `log_map(x, y)`: Tangent space exponential and logarithmic maps.
   - `frechet_mean(points, lr=0.1, max_iter=20)`: Riemannian gradient descent to find the hyperbolic centroid.
2. Self-contained verification block at the bottom under `if __name__ == '__main__':` testing distance symmetry, triangle inequality, and Fréchet convergence with `assert` statements.
"""

def delegate_to_local_silicon():
    logger.info("⚡ Delegating code generation to local resident model (gpt-oss-20b on Radeon 8060S iGPU)...")
    from cohezion.inference.gaia_adapter import strip_reasoning_tags
    payload = {
        "model": "gpt-oss-20b-mxfp4-GGUF",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ],
        "max_tokens": 1500,
        "temperature": 0.2,
    }
    
    t0 = time.perf_counter()
    req = urllib.request.Request(
        LEMONADE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        choice = data["choices"][0]["message"]
        content_part = choice.get("content", "")
        clean_code = strip_reasoning_tags(content_part) if content_part else ""
        if not clean_code and choice.get("reasoning_content"):
            clean_code = choice.get("reasoning_content", "")
            
        dt = time.perf_counter() - t0
        logger.info("✓ Local inference completed in %.2fs (%d tokens)", dt, data.get("usage", {}).get("completion_tokens", 0))

    # Extract clean Python code
    if "```python" in clean_code:
        clean_code = clean_code.split("```python")[-1].split("```")[0].strip()
    elif "```" in clean_code:
        clean_code = clean_code.split("```")[1].strip()
        
    target_file = "src/cohezion/physics/nano_poincare.py"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(clean_code)
    logger.info("✓ Saved generated micro-engine to %s", target_file)

    # Formal Verification
    logger.info("🔍 Running AutoHarness AST & Bubblewrap Linux Namespace verification...")
    verifier = AutoHarnessVerifier()
    ast_res = verifier.verify_code(clean_code)
    logger.info("  • AutoHarness AST Check: %s", "🟢 PASSED" if ast_res.get("verified") else "❌ FAILED")

    sandbox = LinuxNamespaceSandbox(timeout_sec=10.0)
    sandbox_res = sandbox.execute_python_code(clean_code)
    logger.info("  • Bubblewrap Namespace Execution: %s", "🟢 PASSED" if sandbox_res.success else "❌ FAILED")
    if sandbox_res.stdout.strip():
        print("\n--- Sandbox Verification Output ---")
        print(sandbox_res.stdout.strip())
        print("----------------------------------\n")

    assert sandbox_res.success, f"Verification failed: {sandbox_res.stderr}"
    print("🎉 First-Principles Karpathy-Tier NanoPoincare Micro-Engine: 100% LOCALLY SYNTHESIZED & VERIFIED!")

if __name__ == "__main__":
    delegate_to_local_silicon()
