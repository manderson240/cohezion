#!/usr/bin/env python3
"""GAIA local orchestrator — runs the compound build->verify->refine loop on $0 LOCAL inference
(lemonade :13305) with a BMAD Dev->QA structure, escalating to Claude (the ADVISOR tier) ONLY when
the local loop is genuinely stuck. Claude burns near-zero tokens: it is consulted on demand via an
escalation queue, NOT the orchestrator.

Usage:  uv run python scripts/gaia_orchestrator.py "<task>"
Escalations -> ~/.cohezion/advice_queue.jsonl  (paste entries to Claude when they appear).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

LEMONADE = "http://localhost:13305/v1/chat/completions"
PLAN_MODEL = "DeepSeek-Qwen3-8B-GGUF"   # reasoning lane (planning)
DEV_MODEL = "Gemma-4-26B-A4B-it-GGUF"   # generation lane
QA_MODEL = "Bonsai-8B-gguf"             # non-thinking QA judge (the BMAD QA "knot")
ADVICE = Path.home() / ".cohezion" / "advice_queue.jsonl"


def chat(model: str, prompt: str, max_tokens: int = 800) -> str:
    try:
        r = httpx.post(LEMONADE, json={"model": model, "messages": [{"role": "user", "content": prompt}],
                                       "max_tokens": max_tokens, "temperature": 0.2}, timeout=240)
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"(local inference error: {e})"


def qa_judge(task: str, output: str) -> tuple[bool, str]:
    v = chat(QA_MODEL, f"Grade if OUTPUT satisfies TASK.\nTASK: {task}\nOUTPUT:\n{output}\n\n"
                       "Reply ONE line: 'PASS' or 'FAIL: <reason>'.", 120)
    return v.upper().startswith("PASS"), v


def escalate(task: str, question: str, context: str) -> None:
    ADVICE.parent.mkdir(exist_ok=True)
    with ADVICE.open("a") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M"), "task": task,
                            "question": question, "context": context[:600]}) + "\n")
    print(f"\n[ESCALATED → Claude advisor] {question}\n  queued: {ADVICE}  (paste it to Claude for advice)")


def run(task: str, max_rounds: int = 3) -> str | None:
    plan = chat(PLAN_MODEL, f"Plan this task in 1-3 concrete steps (terse):\n{task}", 400)
    print(f"PLAN ({PLAN_MODEL}):\n{plan}\n")
    last = ""
    for rnd in range(1, max_rounds + 1):
        last = chat(DEV_MODEL, f"Task: {task}\nPlan: {plan}\nProduce the complete result.")
        ok, verdict = qa_judge(task, last)
        print(f"[round {rnd}] QA: {verdict[:90]}")
        if ok:
            print(f"\n=== RESULT (local, $0) ===\n{last}")
            return last
        plan = chat(PLAN_MODEL, f"Previous attempt FAILED QA ({verdict[:80]}). Revise the plan:\n{task}", 400)
    escalate(task, f"Local loop failed QA {max_rounds}x — need advice.", f"task={task}\nlast_output={last}")
    return None


if __name__ == "__main__":
    run(" ".join(sys.argv[1:]) or "Write a Python function add(a, b) with a docstring.")
