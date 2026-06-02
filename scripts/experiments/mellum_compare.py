#!/usr/bin/env python3
"""Compare Mellum-4b vs other resident fleet models on code completion.

Dogfoods the falsifiable-eval-harness pattern: fixed task set, word-boundary scoring,
temp=0, honest metrics (correctness + latency). Resident models only (no new loads):
  - Mellum-4b (FIM-native, code-completion specialist) — /completions with FIM tokens
  - Granite-4.1-8B (general, chat) — /chat/completions, prompted to complete
  - llama3.2-1b-FLM on NPU :13306 (fast/weak baseline) — /chat/completions

Honest caveat: Mellum is FIM-native; the chat models are prompted to complete, a format
the task suits less well. We report both correctness AND latency so the tradeoff is visible.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request

ROUTER = "http://localhost:13305/api/v1"
NPU = "http://localhost:13306/api/v1"

# (prefix, expected_substring) — completion should contain the expected code.
TASKS = [
    ("def add(a, b):\n    return ", "a + b"),
    ("def is_even(n):\n    return n % 2 == ", "0"),
    ("def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(", "n - 1"),
    ("def reverse_string(s):\n    return s[", "::-1"),
    ("try:\n    x = 1 / 0\nexcept ", "ZeroDivisionError"),
    ("squares = [x ** 2 for x in ", "range"),
    ("import json\nobj = json.", "loads"),
    ("def clamp(v, lo, hi):\n    return max(lo, min(v, ", "hi"),
]


def _post(url: str, payload: dict) -> tuple[str, float]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 — fixed localhost fleet URL
            body = json.loads(r.read())
        dt = (time.perf_counter() - t0) * 1000
    except Exception as e:
        return f"[err {e}]", (time.perf_counter() - t0) * 1000
    ch = body["choices"][0]
    text = ch.get("text") or ch.get("message", {}).get("content", "") or ""
    return text, dt


def mellum_fim(model: str, prefix: str) -> tuple[str, float]:
    return _post(
        f"{ROUTER}/completions",
        {
            "model": model,
            "prompt": f"<fim_prefix>{prefix}<fim_suffix>\n<fim_middle>",
            "max_tokens": 24,
            "temperature": 0,
        },
    )


def chat_complete(base: str, model: str, prefix: str) -> tuple[str, float]:
    sys_msg = "You complete Python code. Output ONLY the code that continues the snippet — no prose, no fences."
    return _post(
        f"{base}/chat/completions",
        {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prefix},
            ],
            "max_tokens": 32,
            "temperature": 0,
        },
    )


def score(text: str, expected: str) -> int:
    return 1 if re.search(rf"(?<![\w]){re.escape(expected)}", text) else 0


MODELS = [
    ("Mellum-4b", lambda p: mellum_fim("Mellum-4b-base-gguf-mellum-4b-base.Q8_0.gguf", p)),
    ("Granite-8B", lambda p: chat_complete(ROUTER, "Granite-4.1-8B-GGUF", p)),
    ("llama-1b/NPU", lambda p: chat_complete(NPU, "llama3.2-1b-FLM", p)),
]


def main() -> int:
    print(f"Code-completion comparison | {len(TASKS)} tasks | temp=0 | resident models\n")
    print(f"{'task':<28} | " + " | ".join(f"{n:<14}" for n, _ in MODELS))
    print("-" * 80)
    agg: dict[str, list] = {n: [] for n, _ in MODELS}
    for prefix, expected in TASKS:
        label = prefix.strip().split(chr(10))[0][:26]
        cells = []
        for name, fn in MODELS:
            text, ms = fn(prefix)
            ok = score(text, expected)
            agg[name].append((ok, ms))
            cells.append(f"{'✓' if ok else '✗'} {ms:6.0f}ms")
        print(f"{label:<28} | " + " | ".join(f"{c:<14}" for c in cells))
    print("-" * 80)
    summary = {}
    for name, _ in MODELS:
        rows = agg[name]
        acc = sum(ok for ok, _ in rows) / len(rows)
        lat = sum(ms for _, ms in rows) / len(rows)
        summary[name] = {"accuracy": round(acc, 3), "avg_latency_ms": round(lat, 1)}
        print(f"{name:<14} accuracy={acc:.0%}  avg_latency={lat:.0f}ms")
    with open("autoresearch.jsonl", "a") as f:
        f.write(json.dumps({"experiment": "mellum_compare", "summary": summary}) + "\n")
    print("\nlogged -> autoresearch.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
