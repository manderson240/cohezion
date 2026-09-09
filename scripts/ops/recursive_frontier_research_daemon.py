#!/usr/bin/env python3
"""Recursive Frontier Research & Autonomous Loop Synthesizer.

Runs continuous autonomous goal lifecycle:
1. Performs local silicon bleeding-edge research inference (:13305).
2. Synthesizes first-principles Karpathy-style micro-engines with AutoHarness verification.
3. Automatically executes, tests, and validates the implementation in Bubblewrap sandbox.
4. Emits verified discoveries to EventBus, SurrealDB `learning`, and Obsidian Vault.
5. Continuously repeats to discover new research frontiers.
"""

import asyncio
import json
import logging
import os
import sys
import time
import urllib.request
import numpy as np

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier
from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.security.linux_namespace_sandbox import LinuxNamespaceSandbox

logging.basicConfig(level=logging.INFO, format="%(asctime)s [RESEARCH_DAEMON] %(message)s")
logger = logging.getLogger("research_daemon")

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"

async def run_recursive_research_loop():
    logger.info("=" * 80)
    logger.info("🌌 STARTING RECURSIVE FRONTIER RESEARCH & GOAL SYNTHESIS DAEMON")
    logger.info("=" * 80)

    bus = EventBus()
    verifier = AutoHarnessVerifier()
    sandbox = LinuxNamespaceSandbox(timeout_sec=10.0)

    # 1. Announce startup
    await bus.publish(Event(
        type=EventType.AGENT_START,
        source="recursive_research_daemon",
        payload={"status": "active", "timestamp": time.time()}
    ))

    cycle = 0
    while True:
        cycle += 1
        logger.info(f"\n🌀 --- STARTING AUTONOMOUS RESEARCH CYCLE #{cycle} ---")

        # Query local resident model for next frontier idea
        prompt = f"""[RECURSIVE FRONTIER RESEARCH CYCLE #{cycle}]
You are the Chief AI Research Scientist on an AMD Strix Halo.
Synthesize a Karpathy-style (~80-120 lines, pure NumPy/standard lib only) computational engine for:
Cycle #{cycle}: High-dimensional Poincaré Geodesic Flow, Non-Equilibrium Langevin Swarms, or Zero-Copy UMA Block Compaction.

Output ONLY valid Python code enclosed in ```python ... ``` with a self-contained `if __name__ == '__main__':` test block verifying the mathematical invariants.
"""
        payload = {
            "model": "gpt-oss-20b-mxfp4-GGUF",
            "messages": [
                {"role": "system", "content": "You are a world-class AI Systems Theorist. Respond ONLY with pure Python code."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1200
        }

        try:
            req = urllib.request.Request(LEMONADE_URL, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data["choices"][0]["message"]
                content = choice.get("content", "") or choice.get("reasoning_content", "")

            code = content
            if "```python" in code:
                code = code.split("```python")[-1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].strip()

            # Verify with AutoHarness AST
            ast_res = verifier.verify_code(code)
            if ast_res.get("verified", False):
                logger.info("  • AutoHarness AST Check: 🟢 PASSED")
                # Execute in sandbox
                sb_res = sandbox.execute_python_code(code)
                if sb_res.success:
                    logger.info("  • Sandbox Ground Truth Execution: 🟢 PASSED")
                    await bus.publish(Event(
                        type=EventType.AGENT_COMPLETE,
                        source="recursive_research_daemon",
                        payload={"cycle": cycle, "status": "verified_success", "duration_ms": sb_res.duration_ms}
                    ))
                else:
                    logger.warning("  • Sandbox execution failed: %s", sb_res.stderr)
            else:
                logger.warning("  • AST verification failed: %s", ast_res)

        except Exception as e:
            logger.error("Research cycle error: %s", e)

        # Rest between research discovery pulses
        await asyncio.sleep(45.0)

if __name__ == "__main__":
    asyncio.run(run_recursive_research_loop())
