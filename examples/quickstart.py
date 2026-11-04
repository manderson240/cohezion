#!/usr/bin/env python3
"""Cohezion quickstart: three pieces of the agent platform, offline, in about ten seconds.

1. Routing. Classify prompts into a hardware tier with zero model calls.
2. Guardrails. Run two of the CI scanners' self-tests, which plant a known defect and require
   the scanner to go red before it is trusted to go green.
3. Sandbox. Run model-written code out of process under kernel resource limits (bwrap when it
   is installed, rlimits otherwise): a normal call, a forbidden import, and an infinite loop.

Needs no network, credentials, GPU or local inference server. The research RL environment has
its own example: examples/research_manifold_env.py.

Run: uv run python examples/quickstart.py
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path


# Importing cohezion registers model-provider classes (name only, no network) and logs INFO
# noise unrelated to this demo. WARNING and above still surface.
logging.disable(logging.INFO)

REPO = Path(__file__).resolve().parents[1]


def routing() -> None:
    from cohezion.inference.task_classifier import classify

    print("1. Routing (zero model calls)")
    for prompt in (
        "Is this email spam? Answer yes or no.",
        "Write a Python function that parses ISO-8601 dates, with tests.",
        "Prove step by step that the sum of two odd numbers is even, then generalize.",
    ):
        print(f"   {classify(prompt)!s:<40} <- {prompt}")


def guardrails() -> bool:
    print("\n2. Guardrails (each scanner must catch a planted defect first)")
    ok = True
    for scanner in ("dormancy_scan.py", "phantom_attr_scan.py"):
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "ci" / scanner), "--self-test"],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        last = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
        print(f"   {scanner:<22} {last}")
        ok &= proc.returncode == 0
    return ok


def sandbox() -> bool:
    from cohezion.compound.sandboxed_exec import run_untrusted

    print("\n3. Sandbox (out of process, kernel resource limits)")
    ok = run_untrusted("def double(x):\n    return 2 * x", call="double", args=[21])
    print(f"   normal call      -> ok={ok.ok} value={ok.value} isolation={ok.isolation}")
    refused = run_untrusted("import os\ndef f():\n    return os.listdir('/')", call="f")
    print(f"   import os        -> ok={refused.ok} ({refused.error.split(':')[0]})")
    looped = run_untrusted("def spin():\n    while True:\n        pass", call="spin", timeout_s=1)
    how = "CPU-time limit, SIGXCPU" if "rc=-24" in looped.error else looped.error
    print(f"   infinite loop    -> ok={looped.ok} (stopped by the {how})")
    return ok.ok and ok.value == 42 and not refused.ok and not looped.ok


def main() -> int:
    routing()
    passed = guardrails() & sandbox()
    print("\nQuickstart complete." if passed else "\nQuickstart FAILED: see output above.")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
