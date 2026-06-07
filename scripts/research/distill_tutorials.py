#!/usr/bin/env python3
"""Distill external tutorials through the LOCAL fleet ($0) into a research digest.

User directive 2026-06-06: "have local inference work through each of them." Fetches a tutorial's
content (GitHub), extracts text (ipynb cells or .py source), and runs it through lemonade :13305
(Granite-4.1-8B, tool-capable, no-thinking) with a structured distillation prompt. The output is a
per-tutorial digest applying the research filter (technique / cohezion-overlap / transferable lever).

Re-runnable for ALL tutorials by extending TARGETS. Local-only — no cloud, no fabrication: the model
reads the actual tutorial text. Read-only w.r.t. the repo (writes only the digest passed by the caller).
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request

REPO = "Marktechpost/AI-Agents-Projects-Tutorials"
LEMONADE = "http://localhost:13305/api/v1/chat/completions"
MODEL = "Granite-4.1-8B-GGUF"  # no-thinking, tool-capable (hermes-skill validated)


def fetch_raw(path: str) -> str:
    """Raw file bytes via the GitHub contents API (gh handles auth)."""
    out = subprocess.run(
        ["gh", "api", f"repos/{REPO}/contents/{path}", "--jq", ".download_url"],
        capture_output=True, text=True, timeout=30,
    )
    url = out.stdout.strip()
    if not url:
        return ""
    with urllib.request.urlopen(url, timeout=30) as r:  # noqa: S310 (github raw)
        return r.read().decode("utf-8", errors="replace")


def extract_text(name: str, raw: str, *, cap: int = 6000) -> str:
    """ipynb → markdown + code cell text; .py → source. Capped to fit the context budget."""
    if name.endswith(".ipynb"):
        try:
            nb = json.loads(raw)
            parts = []
            for cell in nb.get("cells", []):
                src = "".join(cell.get("source", []))
                if src.strip():
                    parts.append(src)
            text = "\n\n".join(parts)
        except (json.JSONDecodeError, ValueError):
            text = raw
    else:
        text = raw
    return text[:cap]


def distill(name: str, text: str) -> str:
    """One $0 local-inference call → a 3-point structured distillation."""
    prompt = (
        "You are auditing an external AI tutorial for a LOCAL-FIRST compound-AI platform that ALREADY "
        "has: a neuron/learnings memory store (SurrealDB), a semantic cache (nomic-embed 768D), a "
        "FLUME geometric index, an RHO model/skill tournament, a tiered NPU->iGPU->CPU router, and a "
        "compound executor with experiential-learning deposits.\n\n"
        f"TUTORIAL: {name}\n---\n{text}\n---\n\n"
        "In exactly 3 terse sentences: (1) the CORE reusable technique it teaches; (2) does the "
        "platform above likely ALREADY have this (yes/partial/no, one clause why); (3) ONE concrete "
        "transferable lever IF any, else 'no new lever'. No preamble."
    )
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 320,
        "temperature": 0.2,
    }).encode()
    req = urllib.request.Request(LEMONADE, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 (localhost)
            d = json.load(r)
        m = d["choices"][0]["message"]
        return (m.get("content") or m.get("reasoning_content") or "").strip()
    except Exception as e:  # noqa: BLE001 — report failure, never crash the batch
        return f"[distill failed: {type(e).__name__}: {str(e)[:80]}]"


TARGETS = [
    "Agentic AI Memory/Agentic_Zettelkasten_Memory_Martechpost.ipynb",
    "Agentic AI Memory/Persistent_Memory_Personalised_Agentic_AI_Marktechpost.ipynb",
    "Agentic AI Memory/evermem_persistent_agent_os_faiss_sqlite_marktechpost.py",
    "Agentic AI Memory/agentic_ai_with_langgraph_adaptive_memory_reflexion_Marktechpost.ipynb",
    "LLM Evaluation/LLM_Arena_as_a_Judge.ipynb",
    "LLM Evaluation/gepa_reflective_prompt_evolution_feedback_validation_marktechpost.py",
]


def main() -> int:
    targets = sys.argv[1:] or TARGETS
    for path in targets:
        name = path.split("/")[-1]
        raw = fetch_raw(path)
        if not raw:
            print(f"## {name}\n[fetch failed]\n")
            continue
        text = extract_text(name, raw)
        verdict = distill(name, text)
        print(f"## {name}\n{verdict}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
