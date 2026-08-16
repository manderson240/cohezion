#!/usr/bin/env python3
"""Worktree Ground-Truth and Specification Auditor (Local Model Verification).

Scans all active worktrees across:
1. `.worktrees/`
2. `.claude/worktrees/`
3. `/tmp/opencode/`

Audits:
- Branch & Commit hash
- Modified / Uncommitted files
- Key feature files & test coverage
- PR / Spec / Track alignment
- Local Model (`gpt-oss-20b` or `Qwen3.8-27B`) synthesis of active branches & integration wiring.
"""

import asyncio
import json
import subprocess
import time
from pathlib import Path
import httpx

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")


def get_worktree_inventory():
    print("🌿 Analyzing all Git Worktrees...")
    res = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    
    worktrees = []
    current_wt = {}
    for line in res.stdout.strip().split("\n"):
        if not line:
            if current_wt:
                worktrees.append(current_wt)
                current_wt = {}
            continue
        parts = line.split(" ", 1)
        key = parts[0]
        val = parts[1] if len(parts) > 1 else ""
        if key == "worktree":
            current_wt["path"] = val
        elif key == "HEAD":
            current_wt["head"] = val
        elif key == "branch":
            current_wt["branch"] = val.replace("refs/heads/", "")
        elif key == "locked":
            current_wt["locked"] = True

    if current_wt:
        worktrees.append(current_wt)

    # Detailed status per worktree
    detailed = []
    for wt in worktrees:
        wt_path = Path(wt["path"])
        if not wt_path.exists():
            continue
        # Check git status
        status_res = subprocess.run(["git", "status", "--short"], cwd=wt_path, capture_output=True, text=True)
        dirty_files = [l for l in status_res.stdout.strip().split("\n") if l]
        
        # Check specs / docs
        specs = list(wt_path.glob("specs/**/*.md")) + list(wt_path.glob("docs/**/*.md")) + list(wt_path.glob("*.md"))
        
        # Check tests
        tests = list(wt_path.glob("tests/**/*.py"))
        
        detailed.append({
            "name": wt_path.name,
            "path": str(wt_path),
            "branch": wt.get("branch", "detached"),
            "head": wt.get("head", "")[:9],
            "dirty_file_count": len(dirty_files),
            "spec_count": len(specs),
            "test_count": len(tests),
            "sample_dirty_files": dirty_files[:3],
        })

    return detailed


async def audit_with_local_model(worktrees):
    print(f"🤖 Submitting {len(worktrees)} Worktrees to LOCAL model (`Qwen3.8-27B-GGUF-Q5_K_M` via Lemonade on :13305)...")

    summary_data = {
        "total_active_worktrees": len(worktrees),
        "worktrees_summary": [
            {
                "name": wt["name"],
                "branch": wt["branch"],
                "head": wt["head"],
                "dirty_files": wt["dirty_file_count"],
                "specs": wt["spec_count"],
                "tests": wt["test_count"],
            }
            for wt in worktrees[:20]  # First 20 as dense sample
        ],
    }

    prompt = f"""\
You are an expert multi-branch Git worktree and systems integration auditor.
Audit the following live Git worktree landscape for the Cohezion project:

WORKTREE INVENTORY:
```json
{json.dumps(summary_data, indent=2)}
```

Evaluate and report:
1. Worktree Health & Hygiene: Are branches cleanly mapped with test and specification coverage?
2. Integration & Wiring: Are feature branches properly connected to tests and specs rather than orphaned work?
3. Actionable Recommendations: What worktrees should be merged, consolidated, or pruned?
4. Final Score for Worktree Health & Specification Alignment (0.00 to 1.00).
"""

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            "http://localhost:13305/v1/chat/completions",
            json={
                "model": "Qwen3.8-27B-GGUF-Q5_K_M",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.3,
            },
        )
        dt = time.perf_counter() - t0

    if res.status_code != 200:
        print(f"❌ Local model query failed with HTTP {res.status_code}: {res.text}")
        return

    msg = res.json()["choices"][0]["message"]
    verdict = (msg.get("content") or msg.get("reasoning_content") or "").strip()

    print(f"\nLocal Model Worktree Audit Complete in {dt:.2f}s!")
    print("\n" + "=" * 105)
    print("      📋 LOCAL MODEL WORKTREE & SPEC AUDIT REPORT (`Qwen3.8-27B`)")
    print("=" * 105)
    print(verdict)
    print("=" * 105)


async def main():
    worktrees = get_worktree_inventory()
    await audit_with_local_model(worktrees)


if __name__ == "__main__":
    asyncio.run(main())
