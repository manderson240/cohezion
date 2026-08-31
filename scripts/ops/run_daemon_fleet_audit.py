#!/usr/bin/env python3
"""Daemon Upgrade Auditor & Architect Swarm via Ollama Cloud.

Reads all operational daemons in scripts/ops/ and asks DeepSeek-V4-Pro & Qwen3.5-397B:
1. Audit all remaining background runners (e.g. overnight_experiment_runner.py, launch_persistent_long_horizon_daemon.py, launch_autonomous_bbq_worker.py, run_master_dogfooding.py).
2. Check for adherence to Cohezion's Top-Tier Invariant Suite:
   - 0.00 ms AutoHarness AST Action Verification
   - FleetLock concurrency mutex
   - OOMGuard >= 20.0 GiB safety floor
   - HMAC-SHA256 data provenance signing
   - Sheaf consistency cohomology gating (dim H^0, H^1)
   - Real-time HIHO 0.5 acoustic thermodynamic field sonification (432 Hz calibrated dissonance)
   - Dual-Store persistence (SurrealDB + Obsidian Vault)
"""

import asyncio
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(REPO_ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("daemon_upgrade_auditor")


DAEMONS_TO_AUDIT = [
    "scripts/ops/overnight_experiment_runner.py",
    "scripts/ops/launch_persistent_long_horizon_daemon.py",
    "scripts/ops/launch_autonomous_bbq_worker.py",
    "scripts/ops/run_master_dogfooding.py",
]


async def query_model(model_name: str, prompt: str) -> str:
    url = "http://localhost:11434/api/generate"
    data = json.dumps({"model": model_name, "prompt": prompt, "stream": False, "options": {"temperature": 0.1}})
    req = urllib.request.Request(url, data=data.encode("utf-8"), headers={"Content-Type": "application/json"})
    loop = asyncio.get_running_loop()
    resp_data = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=120.0).read().decode("utf-8"))
    res = json.loads(resp_data)
    return res.get("response") or res.get("thinking") or ""


async def audit_daemon(script_rel_path: str):
    file_path = REPO_ROOT / script_rel_path
    if not file_path.exists():
        logger.warning("File not found: %s", script_rel_path)
        return None

    code_content = file_path.read_text()
    prompt = f"""You are a Frontier Systems Architect for Cohezion.
Examine this background daemon script: `{script_rel_path}`

Source Code:
```python
{code_content[:4000]}
```

Evaluate adherence to Cohezion's Top-Tier Invariant Suite:
1. FleetLock concurrency mutex for multi-model arbitration.
2. OOMGuard dynamic floor (>= 20.0 GiB available RAM).
3. 0ms AutoHarness AST action-verification.
4. Sheaf consistency cohomology check (dim H^0, H^1).
5. HMAC-SHA256 data provenance signing & Dual-Store logging.
6. HIHO 0.5 acoustic thermodynamic field sonification.

Provide a concise, rigorous upgrade plan with code enhancements.
"""
    logger.info("Auditing %s with deepseek-v4-pro:cloud...", script_rel_path)
    review = await query_model("deepseek-v4-pro:cloud", prompt)
    return {"script": script_rel_path, "review": review}


async def main():
    logger.info("=" * 80)
    logger.info("STARTING OLLAMA CLOUD DAEMON UPGRADE AUDIT")
    logger.info("=" * 80)

    tasks = [audit_daemon(p) for p in DAEMONS_TO_AUDIT]
    results = await asyncio.gather(*tasks)

    report_lines = ["# Comprehensive Operational Daemon Upgrade Audit\n", f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n", "**Evaluator**: `deepseek-v4-pro:cloud`\n\n---\n"]
    for r in results:
        if r:
            report_lines.append(f"## Daemon: `{r['script']}`\n\n")
            report_lines.append(r["review"].strip())
            report_lines.append("\n\n---\n")

    report_file = REPO_ROOT / "docs/research/daemon_fleet_upgrade_audit.md"
    report_file.write_text("\n".join(report_lines))
    logger.info("✅ Saved comprehensive daemon upgrade audit to %s", report_file)


if __name__ == "__main__":
    asyncio.run(main())
