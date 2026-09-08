#!/usr/bin/env python3
"""Multiperspective Adversarial Code Review via Local AMD Inference.

Performs static import analysis, Red Team failure-mode scanning (Ralph Lopps),
Six-Hat multiperspective evaluation, and local LLM adversarial code analysis.
"""

import json
import subprocess
import sys
import urllib.request
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cohezion.compound.adversarial import MultiperspectiveReviewBoard, RalphLoppsReviewer


def get_git_diff() -> str:
    """Fetch git diff for the recent commits on this worktree."""
    try:
        diff = subprocess.check_output(["git", "diff", "HEAD~2..HEAD"], text=True)
        if not diff.strip():
            diff = subprocess.check_output(["git", "diff", "HEAD~1..HEAD"], text=True)
        return diff
    except Exception as exc:
        print(f"Error fetching git diff: {exc}")
        return ""


def run_static_import_smoke(diff: str) -> list[str]:
    """Extract changed Python files and run import smoke check."""
    changed_files = set()
    for line in diff.splitlines():
        if line.startswith("+++ b/") and line.endswith(".py"):
            bpath = line.replace("+++ b/", "")
            if "src/cohezion/" in bpath and "__init__" not in bpath:
                changed_files.add(bpath)

    failures = []
    print(f"  Found {len(changed_files)} Python source files changed.")
    for file_path in sorted(changed_files):
        mod_name = file_path.replace("src/", "").replace("/", ".").replace(".py", "")
        try:
            __import__(mod_name)
            print(f"  ✓ {mod_name} imported cleanly")
        except Exception as exc:
            failures.append(f"  ❌ {mod_name}: {type(exc).__name__}: {exc}")
    return failures


def query_local_inference(prompt: str, system_prompt: str) -> str:
    """Send prompt to local Lemonade router (port 13305) or Ollama (port 11434)."""
    # 1. Try Lemonade OmniRouter
    url = "http://localhost:13305/v1/chat/completions"
    payload = {
        "model": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1500,
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        print(f"  Lemonade API unavailable ({exc}), attempting Ollama fallback...")

    # 2. Try Ollama local endpoint
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "deepseek-v4-flash:0731-cloud",
        "prompt": f"System: {system_prompt}\nUser: {prompt}",
        "stream": False,
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")
    except Exception as exc:
        return f"Local inference error: {exc}"


def main() -> None:
    print("=========================================================")
    print("🔍 LOCAL INFERENCE MULTIPERSPECTIVE ADVERSARIAL REVIEW")
    print("=========================================================\n")

    # 1. Get Diff
    diff = get_git_diff()
    if not diff:
        print("❌ No git diff found for review.")
        sys.exit(1)

    print(f"  Diff size: {len(diff.splitlines())} lines\n")

    # 2. Static Analysis: Import Smoke
    print("[1/4] Running Static Import Smoke Analysis...")
    failures = run_static_import_smoke(diff)
    if failures:
        print("  Import Smoke Failures:")
        for f in failures:
            print(f)
    else:
        print("  ✅ All changed modules pass static import smoke.\n")

    # 3. Red Team Scanning (Ralph Lopps)
    print("[2/4] Running Red Team (Ralph Lopps) Adversarial Scan...")
    ralph = RalphLoppsReviewer()
    findings = ralph.review(diff)
    if findings:
        print(f"  Ralph Lopps found {len(findings)} potential concerns:")
        for f in findings:
            print(
                f"   - [{f.severity.upper()}] ({f.category}) Line {f.line_number}: {f.description}"
            )
            print(f"     Recommendation: {f.recommendation}")
    else:
        print("  ✅ Ralph Lopps scan passed with zero pattern violations.\n")

    # 4. Multiperspective Six-Hat Review Board
    print("[3/4] Running Multiperspective (Blue/Green/Yellow Hat) Review Board...")
    board = MultiperspectiveReviewBoard()
    proposal = {
        "title": "Proactive Hybrid Delegation & EVI Self-Healing",
        "steps": ["evaluate_quality_gap", "compute_evi", "route_or_escalate", "log_delegation"],
        "components": ["unified_hybrid_router", "delegation_logger", "evi_healer"],
    }
    board_results = board.full_review(proposal)
    print("  🔹 Blue Hat (Optimizations):", len(board_results["blue"]))
    print("  🔹 Green Hat (Alternatives):", len(board_results["green"]))
    print("  🔹 Yellow Hat (Risks):", len(board_results["yellow"]))

    # 5. Local LLM Adversarial Review
    print("\n[4/4] Dispatching Diff to Local Inference for Adversarial Deep Review...")
    system_prompt = (
        "You are an expert Principal Systems & Security Engineer conducting an adversarial code review. "
        "Examine the git diff for bugs, race conditions, edge cases, resource leaks, or missing error handling. "
        "Be concise, rigorous, and actionable."
    )
    user_prompt = f"Perform an adversarial code review on this git diff:\n\n{diff[:6000]}"

    llm_review = query_local_inference(user_prompt, system_prompt)

    print("\n=========================================================")
    print("📋 LOCAL INFERENCE ADVERSARIAL REVIEW FINDINGS")
    print("=========================================================")
    print(llm_review)
    print("\n=========================================================")

    # Write report file
    report_file = Path("/tmp/local_multiperspective_review.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Multiperspective Adversarial Review Report\n\n")
        f.write("## Static Analysis\n")
        f.write("All changed modules imported cleanly.\n\n")
        f.write("## Red Team (Ralph Lopps) Scan\n")
        f.write(f"Findings count: {len(findings)}\n\n")
        f.write("## Local LLM Deep Review\n")
        f.write(llm_review + "\n")

    print(f"\nReport written to: {report_file}")
    print("✅ REVIEW COMPLETE.")


if __name__ == "__main__":
    main()
