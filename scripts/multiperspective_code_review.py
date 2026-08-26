#!/usr/bin/env -S uv run python
"""Multiperspective Adversarial Code Review Orchestrator.

Combines:
  1. Local Inference (Lemonade / :13305) -> Primary code review (e.g. Qwen3-Coder-30B, Bonsai-8B, Gemma-4)
  2. Ollama Cloud Swarm -> Multi-perspective adversarial evaluation (Cost, Accuracy, Security, Performance)
  3. Structured Output & Synthesis -> Unified review report stored in SurrealDB & Vault

Usage:
  python scripts/multiperspective_code_review.py --commit HEAD
  python scripts/multiperspective_code_review.py --commit HEAD --local-model Qwen3-Coder-30B-A3B-Instruct-GGUF
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cohezion.inference.gaia_adapter import build_gaia_llm_tier
from cohezion.review.delegate import collect, run_review


SURREAL_URL = "http://localhost:8001/sql"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()
OLLAMA_URL = "http://localhost:11434/api/generate"
VAULT_DIR = Path.home() / "vaults" / "cohezion-vault" / "reviews"

PERSPECTIVES = {
    "cost_guardian": {
        "model": "gpt-oss:120b-cloud",
        "focus": "Efficiency, redundancy, un-needed code bloat, over-engineering (Ponytail principles)",
    },
    "security_auditor": {
        "model": "deepseek-v4-pro:cloud",
        "focus": "Vulnerabilities, unsanitized inputs, auth bypass, injection risks, unsafe execution",
    },
    "architecture_reviewer": {
        "model": "gemma4:31b-cloud",
        "focus": "API contract preservation, thread safety, async/sync decoupling, error propagation",
    },
}


def query_ollama(model: str, prompt: str, timeout: float = 45.0) -> str:
    """Query an Ollama cloud model."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode())
            return res.get("response", "").strip()
    except Exception as e:
        return f"ERROR ({model}): {e}"


def surreal_write(table: str, record_id: str, data: dict) -> bool:
    """Write record to SurrealDB with sanitized record_id."""
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
            res = json.loads(r.read())
            return bool(isinstance(res, list) and res and res[0].get("status") == "OK")
    except Exception as e:
        print(f"  [surreal] WARN: {e}")
        return False


def _git_diff(commit: str):
    def diff_fn(path: str) -> str:
        proc = __import__("subprocess").run(
            ["git", "show", f"{commit}", "--", path],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            check=False,
        )
        return proc.stdout[:40000]
    return diff_fn


def main() -> int:
    ap = argparse.ArgumentParser(description="Multiperspective Adversarial Code Review")
    ap.add_argument("--commit", default="HEAD", help="Git commit or ref to review")
    ap.add_argument("--local-model", default="Bonsai-8B-gguf", help="Local Lemonade model for base review")
    ap.add_argument("--skip-cloud", action="store_true", help="Skip cloud perspectives")
    args = ap.parse_args()

    print("=== Multiperspective Adversarial Code Review ===")
    print(f"Ref: {args.commit} | Local Model: {args.local_model}")

    # 1. Collect diff & review rules via ocr delegate
    review = collect(commit=args.commit, cwd=REPO)
    if not review.files:
        print("  ⚠ No reviewable files found.")
        return 0

    print(f"  Reviewing {len(review.files)} file(s)...")

    # 2. Local Inference Primary Pass
    diff_fn = _git_diff(args.commit)
    tier = build_gaia_llm_tier(args.local_model, max_tokens=4096)
    local_findings = run_review(review, tier.agent.prompt, diff_fn)

    print("\n--- Local Review Findings ---")
    for path, text in local_findings.items():
        print(f"[{path}]\n{text}\n")

    # 3. Multiperspective Cloud Review Pass
    cloud_findings = {}
    if not args.skip_cloud:
        print("--- Running Multiperspective Adversarial Cloud Swarm ---")
        full_diff_summary = "\n".join(
            [f"File: {f.path}\nDiff:\n{diff_fn(f.path)[:2000]}" for f in review.files]
        )

        for role, pinfo in PERSPECTIVES.items():
            print(f"  -> Invoking [{role}] via {pinfo['model']}...")
            prompt = (
                f"You are an expert adversarial code reviewer acting as [{role}].\n"
                f"Focus area: {pinfo['focus']}.\n\n"
                f"Review the following diff and identify critical defects, risks, or anti-patterns:\n\n"
                f"{full_diff_summary}\n\n"
                f"Format: Bulleted findings with path, line reference, and actionable fix."
            )
            resp = query_ollama(pinfo["model"], prompt)
            cloud_findings[role] = {
                "model": pinfo["model"],
                "focus": pinfo["focus"],
                "report": resp,
            }
            print(f"    ✓ {role} completed ({len(resp.split())} words)")

    # 4. Synthesize Final Report
    report_id = f"review_{args.commit.replace('/', '_')}_{int(time.time())}"
    timestamp = datetime.now(UTC).isoformat()

    report_md = [
        f"# Multiperspective Adversarial Review: {args.commit}",
        f"**Date**: {timestamp}",
        f"**Local Model**: {args.local_model}",
        f"**Files Reviewed**: {len(review.files)}",
        "",
        "## Local Inference Findings",
    ]
    for path, text in local_findings.items():
        report_md.append(f"### `{path}`")
        report_md.append(f"```\n{text}\n```\n")

    if cloud_findings:
        report_md.append("## Multiperspective Cloud Swarm Analysis")
        for role, cdata in cloud_findings.items():
            report_md.append(f"### Role: {role} ({cdata['model']})")
            report_md.append(f"**Focus**: {cdata['focus']}\n")
            report_md.append(cdata['report'])
            report_md.append("")

    final_report_str = "\n".join(report_md)

    # 5. Persist to Vault & SurrealDB
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    vault_file = VAULT_DIR / f"{report_id}.md"
    vault_file.write_text(final_report_str)
    print(f"\n✅ Report written to Vault: {vault_file}")

    db_record = {
        "id": report_id,
        "commit": args.commit,
        "timestamp": timestamp,
        "local_model": args.local_model,
        "files": [f.path for f in review.files],
        "local_findings": local_findings,
        "cloud_findings": cloud_findings,
    }
    if surreal_write("code_review", report_id, db_record):
        print("✅ Review record persisted to SurrealDB (code_review table)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
