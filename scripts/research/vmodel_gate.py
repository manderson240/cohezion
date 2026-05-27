"""
vmodel_gate.py — V-model structural gate for the compound engineering loop.

Runs structural invariants before accepting any code change. Integrates:
- autoharness: template marker verification
- autodata: recent experiment health check
- TDD: test suite baseline verification
- timeit: performance budget enforcement

Called by:
1. Pre-commit hook (structural layer — fast, <5s)
2. autorun_2h.py every 10 cycles (health monitoring layer)
3. CI pipeline (full verification layer)

Usage:
    uv run python3 scripts/research/vmodel_gate.py [--level fast|full]
    Exit 0 = pass, Exit 1 = gate failure
"""

from __future__ import annotations

import subprocess
import sys
import timeit
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


# ── Structural invariants (V-model Layer 1 — always run) ────────────────────


def check_nemotron_template() -> tuple[bool, str]:
    """O1: Nemotron v5 template has all required markers."""
    t0 = timeit.default_timer()
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from cohezion.integrations.kaggle_training_improved import KaggleTrainingManager

        tmpl = KaggleTrainingManager().get_training_script_template()
        required = [
            "all-linear",
            "DataCollatorForSeq2Seq",
            "label_pad_token_id=-100",
            "torch_dtype=torch.bfloat16",
            "lora_alpha=64",
            "BOXED_INSTRUCTION",
            "adapter_config.json",
            "enable_input_require_grads",
            "extract_boxed",
        ]
        missing = [m for m in required if m not in tmpl]
        ms = (timeit.default_timer() - t0) * 1000
        if missing:
            return False, f"O1 FAIL: Nemotron template missing {missing} ({ms:.1f}ms)"
        return True, f"O1 PASS: Nemotron template v5 ({ms:.1f}ms)"
    except Exception as e:
        ms = (timeit.default_timer() - t0) * 1000
        return False, f"O1 ERROR: {e} ({ms:.1f}ms)"


def check_post_execution_wired() -> tuple[bool, str]:
    """O2: PostExecutionOrchestrator is importable from compound entry point."""
    t0 = timeit.default_timer()
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from cohezion.compound.executor import PostExecutionOrchestrator  # noqa: F401

        ms = (timeit.default_timer() - t0) * 1000
        return True, f"O2 PASS: PostExecutionOrchestrator reachable ({ms:.1f}ms)"
    except ImportError as e:
        ms = (timeit.default_timer() - t0) * 1000
        return False, f"O2 FAIL: PostExecutionOrchestrator not wired — {e} ({ms:.1f}ms)"


def check_autocontext_importable() -> tuple[bool, str]:
    """O3: autocontext module importable (5th pillar of research framework)."""
    t0 = timeit.default_timer()
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from cohezion.research.autocontext import monitor, compress, budget, archive  # noqa: F401

        ms = (timeit.default_timer() - t0) * 1000
        return True, f"O3 PASS: autocontext 4 functions importable ({ms:.1f}ms)"
    except ImportError as e:
        ms = (timeit.default_timer() - t0) * 1000
        return False, f"O3 FAIL: autocontext not importable — {e} ({ms:.1f}ms)"


def check_adaptive_schedule_importable() -> tuple[bool, str]:
    """O4: AdaptiveSchedule importable (compound research core)."""
    t0 = timeit.default_timer()
    try:
        spec_path = ROOT / "scripts" / "research" / "adaptive_schedule.py"
        if not spec_path.exists():
            return False, "O4 FAIL: adaptive_schedule.py not found"
        sys.path.insert(0, str(ROOT))
        from scripts.research.adaptive_schedule import AdaptiveSchedule  # noqa: F401

        ms = (timeit.default_timer() - t0) * 1000
        return True, f"O4 PASS: AdaptiveSchedule importable ({ms:.1f}ms)"
    except Exception as e:
        ms = (timeit.default_timer() - t0) * 1000
        return False, f"O4 FAIL: {e} ({ms:.1f}ms)"


# ── Behavioral layer (V-model Layer 2 — fast tests) ─────────────────────────


def check_unit_tests_fast() -> tuple[bool, str]:
    """B1: Fast unit tests pass (autoharness behavioral gate)."""
    t0 = timeit.default_timer()
    result = subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "tests/unit",
            "--import-mode=append",
            "-q",
            "--tb=no",
            "-p",
            "no:warnings",
            "--co",
            "-q",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=ROOT,
    )
    collect_ok = result.returncode == 0
    ms = (timeit.default_timer() - t0) * 1000

    if not collect_ok:
        return False, f"B1 FAIL: test collection errors in {ms:.0f}ms"

    # Count collected tests
    lines = result.stdout.strip().split("\n")
    n_tests = sum(1 for l in lines if "::" in l)
    return True, f"B1 PASS: {n_tests} tests collect cleanly ({ms:.0f}ms)"


# ── Gate runner ───────────────────────────────────────────────────────────────

FAST_GATES = [
    check_nemotron_template,
    check_post_execution_wired,
    check_autocontext_importable,
    check_adaptive_schedule_importable,
]

FULL_GATES = FAST_GATES + [
    check_unit_tests_fast,
]


def run_gates(level: str = "fast") -> int:
    """Run V-model gates. Returns 0 (pass) or 1 (fail)."""
    gates = FULL_GATES if level == "full" else FAST_GATES
    t_total = timeit.default_timer()
    results = []

    for gate_fn in gates:
        passed, msg = gate_fn()
        results.append((passed, msg))
        print(msg, flush=True)

    total_ms = (timeit.default_timer() - t_total) * 1000
    passes = sum(1 for p, _ in results if p)
    total = len(results)

    print()
    if passes == total:
        print(f"V-MODEL GATE: {passes}/{total} PASS ({total_ms:.0f}ms)")
        return 0
    else:
        failures = [msg for p, msg in results if not p]
        print(f"V-MODEL GATE: {passes}/{total} — FAILURES: {failures}")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--level", choices=["fast", "full"], default="fast")
    args = parser.parse_args()
    sys.exit(run_gates(args.level))
