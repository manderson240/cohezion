#!/usr/bin/env python3
"""Dormancy scan — deterministic CI gate (verification-depth.md layer 3).

A load-bearing capability that has NO production consumer (referenced only in tests / its own `def`)
is DORMANT — wired structurally, dead functionally. This is the dominant bug class the 2026-06-30
adversarial reviews kept finding (the regression gate, jepa_coherence, inference_provider, CR1,
moe_router, the 4 never-landed subsystems). The unit tests were all green; the seams were hollow.

This is a CURATED regression guard, NOT a blind whole-graph scan — each entry names a capability and a
regex that matches its CONSUMPTION site (a read/call), pinned to the file that must consume it. If a
future change removes the consumer (re-dormants the capability), the count drops below the floor and
the scan exits non-zero → the commit/CI fails. Curated specifically so it never cries wolf and gets
disabled (the fate of the auto-test-scaffold hook).

Run:  python scripts/ci/dormancy_scan.py            # the gate (exit 1 on dormancy)
      python scripts/ci/dormancy_scan.py --self-test # prove it can go RED before trusting GREEN
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "cohezion"

# (name, consumer_regex, path_relative_to_repo, min_count). The regex matches the CONSUMER (a read or
# a call), NOT the declaration — so neutralizing the consumer drops the count below the floor.
REGISTRY: list[tuple[str, str, str, int]] = [
    ("H1: regression gate FIRES (refine calls _ensure_golden_fixtures)",
     r"self\._ensure_golden_fixtures\(", "src/cohezion/compound/skill_refiner.py", 1),
    ("H2: jepa_coherence CONSUMED by DegradationDetector",
     r"jepa_coherence", "src/cohezion/compound/degradation_detector.py", 1),
    ("ME1: engine feedback consumed by the learner (record call)",
     r"_difficulty_estimator\.record\(", "src/cohezion/compound/skill_refiner.py", 1),
    ("M1: regression run_fn wired live (set in __init__ + factory)",
     r"_regression_run_fn", "src/cohezion/compound/skill_refiner.py", 2),
    ("Lever1: per-task gate_chars drives the cascade entry",
     r"gate_chars", "src/cohezion/inference/orchestrator.py", 2),
]


def count_matches(pattern: str, path_rel: str) -> int:
    """Count regex matches in PRODUCTION .py (excluding tests/ and test_*.py)."""
    p = REPO / path_rel
    files = [p] if p.is_file() else list(p.rglob("*.py"))
    rx = re.compile(pattern)
    total = 0
    for f in files:
        s = str(f)
        if "/tests/" in s or f.name.startswith("test_"):
            continue
        try:
            total += len(rx.findall(f.read_text(errors="ignore")))
        except Exception:
            pass
    return total


def scan(registry: list[tuple[str, str, str, int]]) -> list[str]:
    failures = []
    for name, pattern, path_rel, floor in registry:
        n = count_matches(pattern, path_rel)
        if n < floor:
            failures.append(f"DORMANT: {name} — {n} consumer(s), need >= {floor}  [{pattern} in {path_rel}]")
    return failures


def self_test() -> int:
    """Falsification proof: the scanner MUST flag a guaranteed-dormant sentinel (proves it can go red)
    AND pass a known-wired capability (proves it isn't a blanket false-positive)."""
    sentinel = scan([("sentinel (no consumer exists)", r"__NEVER_EXISTS_DORMANCY_SENTINEL__", "src/cohezion", 1)])
    if not sentinel:
        print("SELF-TEST FAILED: scanner did NOT flag a guaranteed-dormant sentinel — it cannot go red.")
        return 1
    wired = scan([REGISTRY[0]])  # the H1 gate-fires consumer, which is present
    if wired:
        print(f"SELF-TEST FAILED: scanner false-flagged a wired capability: {wired}")
        return 1
    print("SELF-TEST OK: scanner flags the dormant sentinel (red) and passes the wired capability (green).")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    failures = scan(REGISTRY)
    if failures:
        print("DORMANCY SCAN FAILED — a load-bearing capability lost its production consumer:")
        for f in failures:
            print("  " + f)
        print("\nA capability with no consumer is wired structurally but dead functionally (verification-depth.md).")
        return 1
    print(f"dormancy scan OK — all {len(REGISTRY)} curated capabilities have production consumers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
