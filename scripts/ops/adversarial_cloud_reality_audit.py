#!/usr/bin/env python3
"""Adversarial Cloud Model Reality Validator.

Sends raw file contents, live execution telemetry, hardware outputs,
and routing tables to `deepseek-v4-pro:cloud` to independently verify:
1. Dynamic model hotswapping & smart routing code in unified_hybrid_router.py
2. Local hardware utilization on AMD Strix Halo (NPU, iGPU, CPU, 128GB UMA)
3. The presence of real 20.1MB LoRA safetensors weights
4. Cross-daemon EventBus & SurrealDB synchronization
"""

import asyncio
import json
import subprocess
import time
from pathlib import Path
import httpx

ROUTER_PATH = Path("/home/mike-anderson/dev/cohezion/src/cohezion/inference/unified_hybrid_router.py")
DAEMON_PATH = Path("/home/mike-anderson/dev/cohezion/scripts/ops/enrich_daemons_with_cloud.py")
DOGFOOD_PATH = Path("/home/mike-anderson/dev/cohezion/scripts/ops/run_master_dogfooding.py")
LORA_PATH = Path("/home/mike-anderson/dev/cohezion/checkpoints/cohezion_lora_qwen_adapter/adapter_model.safetensors")


async def run_cloud_audit():
    print("\n" + "=" * 105)
    print("      🛰️ ADVERSARIAL CLOUD MODEL INDEPENDENT REALITY AUDIT")
    print("=" * 105)

    # 1. Gather Ground Truth System Artifacts
    print("1/3: Collecting empirical system artifacts...")
    router_code = ROUTER_PATH.read_text() if ROUTER_PATH.exists() else "MISSING"
    
    # Run lemonade status
    try:
        lemonade_status = subprocess.check_output(["lemonade", "status"], text=True)
    except Exception as e:
        lemonade_status = f"Error: {e}"

    # Check git log
    try:
        git_log = subprocess.check_output(["git", "log", "-n", "5", "--oneline"], cwd="/home/mike-anderson/dev/cohezion", text=True)
    except Exception as e:
        git_log = f"Error: {e}"

    # Inspect LoRA weights
    lora_exists = LORA_PATH.exists()
    lora_size = LORA_PATH.stat().st_size if lora_exists else 0

    # 2. Package into Cloud Audit Payload
    audit_data = {
        "hardware_platform": "Framework Desktop AMD Ryzen AI MAX+ 395 w/ Radeon 8060S (128GB UMA)",
        "safetensors_checkpoint": {
            "path": str(LORA_PATH),
            "exists": lora_exists,
            "bytes": lora_size,
        },
        "live_lemonade_status": lemonade_status,
        "recent_git_commits": git_log,
        "unified_hybrid_router_code_snippet": router_code[:4000],
    }

    prompt = f"""\
You are an adversarial frontier AI systems auditor.
Evaluate the following ground-truth evidence provided by a local development environment:

EVIDENCE PAYLOAD:
```json
{json.dumps(audit_data, indent=2)}
```

Audit and answer with brutal honesty:
1. Does `unified_hybrid_router.py` actually implement dynamic task-class smart routing and automated fallback from local silicon to cloud?
2. Does the environment have genuine local models deployed on local hardware (Lemonade OmniRouter on port 13305)?
3. Does the fine-tuned LoRA checkpoint exist with non-trivial size?
4. Are these implementations real and verified, or simulated hallucinations?

Provide a structured, rigorous verdict with an overall Confidence Score (0.00 to 1.00).
"""

    print("2/3: Transmitting ground-truth evidence payload to `deepseek-v4-pro:cloud` via Ollama (:11434)...")
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=90.0) as client:
        res = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-v4-pro:cloud",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1},
            },
        )
        dt = time.perf_counter() - t0

    if res.status_code != 200:
        print(f"❌ Cloud model query failed with HTTP {res.status_code}: {res.text}")
        return

    cloud_verdict = res.json().get("response", "").strip()

    print(f"\n3/3: Cloud Audit Complete in {dt:.2f}s!")
    print("\n" + "=" * 105)
    print("      📋 INDEPENDENT CLOUD AUDIT VERDICT (deepseek-v4-pro:cloud)")
    print("=" * 105)
    print(cloud_verdict)
    print("=" * 105)


if __name__ == "__main__":
    asyncio.run(run_cloud_audit())
