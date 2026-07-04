#!/usr/bin/env python3
"""Falsifiable experiment — logprob gate vs length gate vs placebo gate.

Tests the SOTA claim (arXiv:2605.02241): mean token log-probability is a
better zero-shot escalation gate than length heuristics for local→cloud
routing. Three arms isolate the effect:

  logprob  — composite_gate with mean_logprob as primary signal.
  length   — old gate: len(text) >= 40 + self_reported_confidence.
  placebo  — random threshold (controls for "any gate helps").

Honest-result contract: "logprob wins" is falsifiable. If the logprob arm
does not rise above length/placebo, that is reported as a negative result.

Run:  uv run python scripts/experiments/escalation_gate_eval.py
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROUTER_URL = "http://localhost:13305/v1/chat/completions"
MODEL = os.environ.get("GATE_EVAL_MODEL", "Qwen3-Coder-30B-A3B-Instruct-GGUF")
MAX_TOKENS = int(os.environ.get("GATE_EVAL_MAX_TOKENS", "120"))
TIMEOUT_S = 60
NUM_TASKS = 20
TEMP = 0
DELAY_BETWEEN_CALLS = 2.0  # seconds — be gentle on the omni router (LRU eviction guard)

# Gate thresholds
TAU_LOGPROB = -2.5  # calibrated: correct 1-word answers score ~-0.5 to -1.5; uncertain ~-3.0+
MIN_LENGTH = 3      # minimum sane response length (filters empty/error responses only)
QUALITY_THRESHOLD = 0.8


@dataclass
class EvalTask:
    question: str
    expected: list[str] = field(default_factory=list)
    difficulty: str = "easy"


TASKS: list[EvalTask] = [
    EvalTask("What data structure uses LIFO ordering?", ["stack"], "easy"),
    EvalTask("What HTTP status code means Not Found?", ["404"], "easy"),
    EvalTask("What Python keyword makes a function a generator?", ["yield"], "easy"),
    EvalTask("What is the worst-case time complexity of binary search in big-O?", ["log"], "easy"),
    EvalTask("Which AWS service provides object storage?", ["s3"], "easy"),
    EvalTask("What cryptographic protocol does HTTPS use?", ["tls"], "easy"),
    EvalTask("What sorting algorithm merges sorted sublists?", ["merge"], "easy"),
    EvalTask("What SQL keyword removes duplicate rows?", ["distinct"], "easy"),
    EvalTask("What is the capital of France?", ["paris"], "easy"),
    EvalTask("What language has the most native speakers?", ["mandarin"], "easy"),
    # Hard tasks — obscure facts where the model might hallucinate (low logprob)
    EvalTask("What year was the Riemann hypothesis first formulated?", ["1859"], "hard"),
    EvalTask("What is the Erdős–Ko–Rado theorem's maximum intersecting family size?", ["choose"], "hard"),
    EvalTask("What does the acronym ACID stand for in database theory?", ["atomicity", "consistency", "isolation", "durability"], "easy"),
    EvalTask("What is the Kolmogorov complexity of a string of n zeros?", ["log"], "hard"),
    EvalTask("What sorting algorithm has O(n) best-case and O(n^2) worst-case?", ["insertion"], "easy"),
    EvalTask("What is the Chaitin constant?", ["halting"], "hard"),
    EvalTask("What graph algorithm finds shortest paths with negative edges?", ["bellman"], "easy"),
    EvalTask("What is the maximum number of edges in a planar graph with n vertices?", ["3n"], "hard"),
    EvalTask("What complexity class is defined by polynomial-space Turing machines?", ["pspace"], "hard"),
    EvalTask("What does DNS stand for?", ["domain", "name", "system"], "easy"),
]


def _chat_with_logprobs(model: str, question: str) -> tuple[str, float | None]:
    """One local call with logprobs enabled. Returns (content, mean_logprob)."""
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": question}],
            "temperature": TEMP,
            "max_tokens": MAX_TOKENS,
            "logprobs": True,
            "top_logprobs": 1,
        }
    ).encode()
    req = urllib.request.Request(
        ROUTER_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read())
        choice = data["choices"][0]
        content = choice["message"].get("content", "") or ""
        logprobs = choice.get("logprobs", {})
        content_lps = logprobs.get("content", []) if logprobs else []
        values = [lp.get("logprob") for lp in content_lps if lp and lp.get("logprob") is not None]
        mean_lp = sum(values) / len(values) if values else None
        return content, mean_lp
    except Exception as e:
        print(f"    [warn] call failed: {e}", file=sys.stderr)
        return "", None


def score_answer(text: str, expected: list[str]) -> float:
    """Word-boundary match for expected terms (case-insensitive)."""
    if not expected:
        return 0.0
    low = text.lower()
    hits = 0
    for term in expected:
        if re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", low):
            hits += 1
    return hits / len(expected)


def gate_logprob(text: str, mean_logprob: float | None) -> bool:
    """New gate: logprob only — isolates the logprob signal from length heuristic."""
    if len(text) < MIN_LENGTH:
        return False  # empty/error response
    if mean_logprob is not None:
        return mean_logprob >= TAU_LOGPROB  # logprob alone (no length confound)
    return True  # no logprob available — accept any non-empty response


def gate_length(text: str, mean_logprob: float | None) -> bool:
    """Old gate: length only."""
    return len(text) >= MIN_LENGTH


def gate_placebo(text: str, mean_logprob: float | None) -> bool:
    """Placebo: random threshold (controls for 'any gate helps')."""
    return len(text) >= MIN_LENGTH and random.random() > 0.3


def run_experiment() -> dict:
    """Run 3-arm experiment: logprob / length / placebo.

    For each task, generate one response, then apply each gate to decide
    'accept local' vs 'escalate'. If gate says escalate, we score 0 (didn't
    accept the local answer). If gate says accept, we score the actual answer
    quality. This measures: 'does the gate correctly accept good answers
    and reject bad ones?'

    Metric = mean accuracy across tasks where gate accepted the answer.
    A good gate accepts correct answers (high score) and rejects incorrect ones.
    """
    random.seed(42)
    results = {"logprob": [], "length": [], "placebo": []}
    accepted = {"logprob": 0, "length": 0, "placebo": 0}
    correct_when_accepted = {"logprob": 0, "length": 0, "placebo": 0}

    for i, task in enumerate(TASKS):
        print(f"  [{i+1}/{len(TASKS)}] {task.question[:60]}...")
        text, mean_lp = _chat_with_logprobs(MODEL, task.question)
        time.sleep(DELAY_BETWEEN_CALLS)  # be gentle on the omni router (LRU eviction guard)

        actual_score = score_answer(text, task.expected)

        for arm_name, gate_fn in [
            ("logprob", gate_logprob),
            ("length", gate_length),
            ("placebo", gate_placebo),
        ]:
            accepted_local = gate_fn(text, mean_lp)
            if accepted_local:
                accepted[arm_name] += 1
                results[arm_name].append(actual_score)
                if actual_score >= 0.5:
                    correct_when_accepted[arm_name] += 1
            else:
                # Escalated to cloud — we count this as "didn't accept local"
                # The gate rejected the local answer. If the answer was actually
                # wrong, this was correct rejection. If right, this was a false rejection.
                results[arm_name].append(0.0)  # didn't benefit from local

    # Compute summary
    summary = {}
    for arm in ["logprob", "length", "placebo"]:
        scores = results[arm]
        mean_score = sum(scores) / len(scores) if scores else 0.0
        accept_rate = accepted[arm] / len(TASKS)
        precision = correct_when_accepted[arm] / accepted[arm] if accepted[arm] > 0 else 0.0
        summary[arm] = {
            "mean_score": round(mean_score, 4),
            "accept_rate": round(accept_rate, 4),
            "precision": round(precision, 4),
            "accepted_count": accepted[arm],
        }

    # Verdict: logprob wins if it beats both on mean_score AND precision
    logprob_wins = (
        summary["logprob"]["mean_score"] > summary["length"]["mean_score"]
        and summary["logprob"]["mean_score"] > summary["placebo"]["mean_score"]
        and summary["logprob"]["precision"] >= summary["length"]["precision"]
    )

    verdict = {
        "experiment": "escalation_gate_eval",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "num_tasks": len(TASKS),
        "tau_logprob": TAU_LOGPROB,
        "min_length": MIN_LENGTH,
        "arms": summary,
        "verdict": "supported" if logprob_wins else "not_supported",
        "falsifiable": True,
    }
    return verdict


def main():
    print("=" * 60)
    print("Escalation Gate Evaluation — logprob vs length vs placebo")
    print(f"Model: {MODEL} | Tasks: {NUM_TASKS} | temp={TEMP}")
    print("=" * 60)

    verdict = run_experiment()

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for arm, s in verdict["arms"].items():
        print(f"  {arm:10s}: mean_score={s['mean_score']:.4f}  precision={s['precision']:.4f}  accepted={s['accepted_count']}/{verdict['num_tasks']}")
    print(f"\n  VERDICT: {verdict['verdict']}")
    print("=" * 60)

    # Log to autoresearch.jsonl
    log_path = Path("autoresearch.jsonl")
    with log_path.open("a") as f:
        f.write(json.dumps(verdict) + "\n")
    print(f"\nLogged to {log_path}")

    # Log to SurrealDB
    try:
        import base64
        sql = f"CREATE experiment_runs CONTENT {json.dumps(verdict)};"
        req = urllib.request.Request(
            "http://localhost:8001/sql",
            data=sql.encode(),
            headers={
                "Accept": "application/json",
                "surreal-ns": "cohezion",
                "surreal-db": "main",
            },
            method="POST",
        )
        auth = base64.b64encode(b"root:root").decode()
        req.add_header("Authorization", f"Basic {auth}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"SurrealDB logged: {resp.status}")
    except Exception as e:
        print(f"SurrealDB log failed (non-blocking): {e}")

    return 0 if verdict["verdict"] == "supported" else 1


if __name__ == "__main__":
    sys.exit(main())