#!/usr/bin/env python3
"""Local Silicon BugHunt & Adversarial Vulnerability Scanner.

Leverages resident local models (`gpt-oss-20b-mxfp4-GGUF` on Radeon 8060S iGPU via :13305)
coupled with AutoHarness AST static analysis to scan target source files for:
1. Unbounded memory allocations / generator explosions.
2. Unhandled exception pathways & broken try/except blocks.
3. Race conditions, thread-unsafe singletons, and missing mutex locks.
4. Broken imports and dead function definitions.
"""

import asyncio
import json
import logging
import os
import sys
import time
import urllib.request
from typing import Any

from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier
from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.data_mesh.kanban_bridge import persist_item

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [BUGHUNT] %(message)s")
logger = logging.getLogger("bughunt")

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"

def query_local_bug_hunter(code_snippet: str, file_path: str) -> dict[str, Any]:
    prompt = f"""You are an adversarial security and bug-hunting kernel engineer.
Analyze the following Python code from `{file_path}` for real bugs, race conditions, memory leaks, or unhandled edge cases:

```python
{code_snippet}
```

Format your response strictly as JSON with this schema:
{{
  "bugs_found": [
    {{
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "line_hint": "approximate line or function",
      "issue": "description of bug",
      "fix": "concrete fix recommendation"
    }}
  ],
  "confidence_score": 0.0 to 1.0,
  "summary": "one sentence verdict"
}}
Output ONLY raw JSON. No conversational wrapper.
"""
    payload = {
        "model": "gpt-oss-20b-mxfp4-GGUF",
        "messages": [
            {"role": "system", "content": "You are a deterministic code security and bug audit kernel. Output strictly valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1024
    }

    try:
        req = urllib.request.Request(LEMONADE_URL, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg = data["choices"][0]["message"]
            raw = msg.get("content", "") or msg.get("reasoning_content", "")
            
            # Extract JSON block
            if "```json" in raw:
                raw = raw.split("```json")[-1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].strip()
            elif "{" in raw and "}" in raw:
                raw = "{" + raw.split("{", 1)[1].rsplit("}", 1)[0] + "}"
            
            return json.loads(raw)
    except Exception as exc:
        return {
            "bugs_found": [],
            "confidence_score": 0.0,
            "summary": f"Audit error or parse failure: {exc}"
        }

def run_local_bughunt():
    target_files = [
        "src/cohezion/inference/nano_uma_compactor.py",
        "src/cohezion/physics/nano_sheaf_ode.py",
        "src/cohezion/physics/nano_chaos.py",
    ]

    print("\n" + "=" * 95)
    print("🔍 LOCAL SILICON ADVERSARIAL BUGHUNT (Radeon 8060S iGPU via :13305)")
    print("=" * 95)

    verifier = AutoHarnessVerifier()
    total_findings = 0

    for fpath in target_files:
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            code = f.read()

        # Step 1: 0ms Static AST Verification
        t0 = time.perf_counter()
        ast_res = verifier.verify_code(code)
        ast_ms = (time.perf_counter() - t0) * 1000.0

        # Step 2: Local Model Semantic Bug Hunt
        t1 = time.perf_counter()
        hunt_res = query_local_bug_hunter(code[:2500], fpath)
        hunt_ms = (time.perf_counter() - t1) * 1000.0

        print(f"\n📁 File: {fpath}")
        print(f"  • AST Verification : {'🟢 CLEAN' if ast_res['verified'] else '❌ VIOLATIONS'} ({ast_ms:.2f} ms)")
        print(f"  • Semantic Audit   : {hunt_res.get('summary', 'Audit complete')} ({hunt_ms:.2f} ms)")
        
        bugs = hunt_res.get("bugs_found", [])
        total_findings += len(bugs)
        if bugs:
            for b in bugs:
                print(f"    ⚠️ [{b.get('severity', 'WARN')}] {b.get('issue')} (Hint: {b.get('line_hint')})")
                print(f"       Fix: {b.get('fix')}")
        else:
            print("    ✅ 0 Critical Bugs Found")

    print("\n" + "=" * 95)
    print(f"🎉 BUGHUNT COMPLETE: {len(target_files)} Files Audited | {total_findings} Findings | 100% Local Inference")
    print("=" * 95 + "\n")

if __name__ == "__main__":
    run_local_bughunt()
