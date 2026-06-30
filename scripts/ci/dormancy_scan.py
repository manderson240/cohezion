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
    # M1/Lever1 (review fix): pin to the CONSUMPTION read, not the bare identifier — the old
    # `_regression_run_fn`/`gate_chars` floors were satisfied by the `=None` decl + a comment, so the
    # guard stayed GREEN with every consumer deleted (the exact false-GREEN this scan forbids).
    ("M1: regression run_fn CONSUMED (refine reads it to gate)",
     r"self\._regression_run_fn is not None", "src/cohezion/compound/skill_refiner.py", 1),
    ("Lever1: per-task gate_chars CONSUMED (override branch reads it)",
     r"gate_chars is not None", "src/cohezion/inference/orchestrator.py", 1),
]

# Known-dormant capabilities (CONFIRMED by review, intentionally NOT yet wired). Reported as a NOTICE
# (not a failure) so the scan never falsely claims "all clear" while these sit dormant outside the
# guarded set — addressing the curation-coverage gap honestly instead of pretending it doesn't exist.
KNOWN_DORMANT: list[str] = [
    "CR1 _recompute_tier_at_compaction — no production boundary fires it (intentional callable; harness-documented)",
    "get_pending_approvals — write side consumed, READ side has no operator surface (HITL gap)",
]


def count_matches(pattern: str, path_rel: str) -> int:
    """Count regex matches in PRODUCTION .py (excluding tests/ and test_*.py), SKIPPING full-line
    comments so a `# ... pattern ...` comment can't satisfy a consumer floor (review fix: the old
    raw-text grep let a comment + a declaration count as 'consumers')."""
    p = REPO / path_rel
    files = [p] if p.is_file() else list(p.rglob("*.py"))
    rx = re.compile(pattern)
    total = 0
    for f in files:
        s = str(f)
        if "/tests/" in s or f.name.startswith("test_"):
            continue
        try:
            for line in f.read_text(errors="ignore").splitlines():
                if line.lstrip().startswith("#"):  # full-line comment — never a consumer
                    continue
                total += len(rx.findall(line))
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
    if KNOWN_DORMANT:
        print(f"NOTICE — {len(KNOWN_DORMANT)} capability(ies) known-dormant and intentionally unguarded:")
        for d in KNOWN_DORMANT:
            print("  - " + d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
