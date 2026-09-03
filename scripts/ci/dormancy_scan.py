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
    (
        "H1: regression gate FIRES (refine calls _ensure_golden_fixtures)",
        r"self\._ensure_golden_fixtures\(",
        "src/cohezion/compound/skill_refiner.py",
        1,
    ),
    # AQ1/AQ5 (2026-08-30): promoted OUT of KNOWN_DORMANT. quality_eval.evaluate was dormant on the
    # production path — its only consumer was AutoDQA, which make_executor never built, so the whole
    # type-aware evaluator (and the autodqa_results table that model/training_data.py reads) had no
    # producer. Two pins, one per link, so breaking EITHER re-fails: the factory must inject the
    # evaluator and the executor must actually call it.
    # NOTE: there is deliberately NO pin binding this to SkillRefiner.quality_score. The scores are
    # escalation-gate verdicts, not correctness — aliasing them into the learner is guarded AGAINST
    # by tests/compound/test_autodqa_quality_wiring.py::TestAQ6ScaleMismatch.
    (
        "AQ1: executor CONSUMES the quality evaluator (evaluates output text)",
        r"self\._quality_evaluator\.evaluate\(",
        "src/cohezion/compound/executor.py",
        1,
    ),
    (
        "AQ5: make_executor INJECTS the AutoDQA quality evaluator",
        r"kwargs\[.quality_evaluator.\] = AutoDQA\(",
        "src/cohezion/compound/executor_factory.py",
        1,
    ),
    (
        "H2: jepa_coherence CONSUMED by DegradationDetector",
        r"jepa_coherence",
        "src/cohezion/compound/degradation_detector.py",
        1,
    ),
    (
        "ME1: engine feedback consumed by the learner (record call)",
        r"_difficulty_estimator\.record\(",
        "src/cohezion/compound/skill_refiner.py",
        1,
    ),
    # DQ (2026-08-30): quality_eval.evaluate was KNOWN_DORMANT below ("dormant ON THE
    # PRODUCTION PATH"). The chain was broken in TWO places and needs a floor on each,
    # because either half alone leaves the DegradationDetector quality_score branch
    # (degradation_detector.py:705) structurally unreachable. Pinned to the CONSUMPTION
    # seams per the M1/Lever1 lesson above -- a floor on `_dqa_gate` alone would be
    # satisfied by the `=None` declaration with every call site deleted.
    (
        "DQ2 producer: execute_task CONSUMES the DQA gate (output quality score is produced)",
        r"_dqa_gate\.evaluate\(",
        "src/cohezion/compound/executor.py",
        1,
    ),
    (
        "DQ4 forwarding: quality_score folded into degradation_metrics (detector can SEE it)",
        r"degradation_metrics\[\"quality_score\"\]",
        "src/cohezion/compound/executor.py",
        1,
    ),
    # Pinned to the ASSIGNMENT, not to the constructor's flags: a floor on
    # `AutoDQA(persist=False` would also go red on a legitimate change to the
    # persist/notify defaults, i.e. it would guard more than its name claims.
    (
        "DQ7 factory: ExecutorFactory.create auto-creates the AutoDQA gate",
        r"dqa_gate = AutoDQA\(",
        "src/cohezion/compound/executor_factory.py",
        1,
    ),
    # M1/Lever1 (review fix): pin to the CONSUMPTION read, not the bare identifier — the old
    # `_regression_run_fn`/`gate_chars` floors were satisfied by the `=None` decl + a comment, so the
    # guard stayed GREEN with every consumer deleted (the exact false-GREEN this scan forbids).
    (
        "M1: regression run_fn CONSUMED (refine reads it to gate)",
        r"self\._regression_run_fn is not None",
        "src/cohezion/compound/skill_refiner.py",
        1,
    ),
    (
        "Lever1: per-task gate_chars CONSUMED (override branch reads it)",
        r"gate_chars is not None",
        "src/cohezion/inference/orchestrator.py",
        1,
    ),
    (
        "H1-grounding: _ensure_golden_fixtures passes ground_fn (grounding LIVE → gate can BITE)",
        r"ground_fn=ground",
        "src/cohezion/compound/skill_refiner.py",
        1,
    ),
    # BMAD qa_gate P0: pin to the ADVISORY consumption seam — refine() must CALL qa_gate.evaluate.
    # Removing the seam (re-dormanting the gate) drops the count below the floor → scan goes RED.
    (
        "qa_gate P0: refine() CONSUMES qa_gate.evaluate (advisory 4-state gate FIRES)",
        r"_qa_gate\.evaluate\(",
        "src/cohezion/compound/skill_refiner.py",
        1,
    ),
    # Quarter-on-a-String knot: execute_task's success verdict is gated by the QA-judge
    # lane, NOT bool(strip()). Pin to the CALL (`_judge_quality(self._base_url`) so the
    # def line can't satisfy the floor — removing the call re-dormants the gate → RED.
    (
        "Knot: local_executor success gated by QA-judge lane (_judge_quality CONSUMED)",
        r"_judge_quality\(self\._base_url",
        "src/cohezion/compound/autonomous_loop/local_executor.py",
        1,
    ),
    # Memory consolidation: the LoopCoordinator end-of-cycle trigger must CALL consolidate() — the
    # automated episode->semantic-fact promotion loop (Elastic deferred-consolidation gap). Pin to
    # the call; removing it re-dormants the consolidator (manual /learn promotion only) -> RED.
    (
        "MemConsolidate: LoopCoordinator fires consolidate() each cycle (episode->semantic promotion)",
        r"consolidator\.consolidate\(",
        "src/cohezion/compound/autonomous_loop/coordinator.py",
        1,
    ),
    # Cognitive-profile harness (P1-P3 of the AGI cognitive-framework /goal): the CLI must CONSUME
    # run_profile(). Removing the call re-dormants the harness (a scorecard nobody runs) -> scan RED.
    (
        "CogProfile: cognitive_profile_cli CONSUMES run_profile() (10-faculty scorecard FIRES)",
        r"run_profile\(",
        "scripts/eval/cognitive_profile_cli.py",
        1,
    ),
    # FAPO failure-path loop (verification-depth.md #2 — "consumption, not declaration"). Before this
    # session's fix, refine() was ONLY ever called on SUCCESS: a failed execution never reached
    # FailureAttributor.classify(), and refine()'s own failure_attribution branch was unreachable from
    # production (green unit tests, dormant seam — the exact failure class this scan exists to catch).
    # Four pins guard both halves of the closed loop so a future refactor can't silently re-dormant it:
    (
        "FA-exec: executor failure branch CONSUMES FailureAttributor().classify() on a failed execution",
        r"FailureAttributor\(\)\.classify\(",
        "src/cohezion/compound/executor.py",
        1,
    ),
    # Pinned to the kwarg name (not `=attribution`, the current variable name) — a harmless
    # local rename of the passed variable must not silently re-green a re-dormanted call.
    # Safe to broaden: `path_rel` scopes this to executor.py alone, whose only occurrence of
    # this literal IS the consumer line (verified; no docstring/comment collisions in this file).
    (
        "FA-refine: executor failure branch CONSUMES refine(failure_attribution=...) (FAPO path reachable)",
        r"failure_attribution=",
        "src/cohezion/compound/executor.py",
        1,
    ),
    (
        "FM-retrieve: _generate_failure_signal CONSUMES failure_memory.retrieve() before generic template",
        r"self\._failure_memory\.retrieve\(",
        "src/cohezion/compound/skill_refiner.py",
        1,
    ),
    (
        "FM-record: L1 refinement CONSUMES failure_memory.record() to store the new (failure, fix) pair",
        r"self\._failure_memory\.record\(",
        "src/cohezion/compound/skill_refiner.py",
        1,
    ),
    # Daily-researcher lanes. Each real lane lived in researcher/lanes/ while an in-file
    # class of the SAME NAME in daily_researcher.py shadowed it, so DailyResearcher built
    # the stub and the real lane never ran (model_scout fixed in cbb33ec69, the other three
    # in 03154f905 + 9a9091979). This scan reported "all clear" throughout, because no lane
    # was curated -- the gap that let the defect live.
    #
    # Pin the LAZY IMPORT, not the `self.<lane> = ...(self)` assignment: the assignment is
    # byte-identical in the stub and real worlds (the bare name just resolves module-locally),
    # so it cannot discriminate. The function-local import is what makes the name resolve to
    # researcher.lanes.*; delete it and the stub wins again -> count drops -> RED.
    # The lanes' dry-run notes were byte-identical to the stubs' too, so no output-based
    # check would work here either.
    (
        "Lane1: DailyResearcher.__init__ imports the REAL ModelScoutLane (not an in-file stub)",
        r"from cohezion\.researcher\.lanes\.model_scout import ModelScoutLane",
        "src/cohezion/researcher/daily_researcher.py",
        1,
    ),
    (
        "Lane2: DailyResearcher.__init__ imports the REAL HarnessPaperLane (not an in-file stub)",
        r"from cohezion\.researcher\.lanes\.harness_paper import HarnessPaperLane",
        "src/cohezion/researcher/daily_researcher.py",
        1,
    ),
    (
        "Lane3: DailyResearcher.__init__ imports the REAL DatameshSynthesisLane (not an in-file stub)",
        r"from cohezion\.researcher\.lanes\.datamesh_synthesis import DatameshSynthesisLane",
        "src/cohezion/researcher/daily_researcher.py",
        1,
    ),
    (
        "Lane4: DailyResearcher.__init__ imports the REAL VerifyEvolveLane (not an in-file stub)",
        r"from cohezion\.researcher\.lanes\.verify_evolve import VerifyEvolveLane",
        "src/cohezion/researcher/daily_researcher.py",
        1,
    ),
]

# Known-dormant capabilities (CONFIRMED by review, intentionally NOT yet wired). Reported as a NOTICE
# (not a failure) so the scan never falsely claims "all clear" while these sit dormant outside the
# guarded set — addressing the curation-coverage gap honestly instead of pretending it doesn't exist.
KNOWN_DORMANT: list[str] = [
    "CR1 _recompute_tier_at_compaction — no production boundary fires it (intentional callable; harness-documented)",
    "get_pending_approvals — write side consumed, READ side has no operator surface (HITL gap)",
    # Constrained-decoding trio (2026-07-28). All three answer "how do we constrain a model's
    # output?", all three are dormant, and NONE knew about the others — so a 4th was nearly built.
    # Listed here so the next person FINDS them instead of implementing a fifth. Live capability
    # facts: tests/inference/test_recipe_constraint_support.py (RC1).
    "structured_npu.npu_structured_json — dormant AND its core claim is FALSIFIED (flm/NPU ignores "
    "`grammar` silently on Lemonade 11.5.0). Wiring target: retarget at a llamacpp recipe model",
    "transition_controller.enum_schema — works (response_format enum, llamacpp lanes) but has no "
    "production caller. Wiring target: the agentic-loop next-state pick it was written for "
    "(one unrepeated probe suggested this path is costlier than bare GBNF — n=1, not established)",
    # quality_eval.evaluate — CLOSED 2026-08-30, promoted out of this list into three GUARDED
    # floors above (DQ2 producer / DQ4 forwarding / DQ7 factory). Kept as a comment because the
    # shape of the gap is the lesson: a consumer-grep said "wired" (DegradationDetector really
    # does read metrics["quality_score"]) while the chain was broken TWICE — nothing produced
    # the key, and `degradation_metrics` was a fresh 5-key dict that would not have carried it
    # anyway. Trace the dict that is actually PASSED, not the identifier that is read.
    "RiemannianGlideTrajectory — geodesic integration made CORRECT 2026-07-29 (was silently "
    "straight-line under any curved metric) but has NO production consumer: only "
    "physics/__init__ re-exports it. INVESTIGATED 2026-07-29 — do NOT wire it: "
    "LagrangianDynamics (physics/lagrangian.py:132) already calls "
    "metric.geodesic_acceleration and integrates with VERLET (2nd-order, vs this class's "
    "1st-order Euler-Cromer) plus force terms, and is already live in ManifoldEnv "
    "(environments/manifold_env.py:176). It is a strict superset; adding a consumer here "
    "would duplicate a working path with a worse integrator. Correct-and-dormant, "
    "deliberately — kept as the small dependency-free primitive (pure-Python lists, no "
    "numpy at import) that LagrangianDynamics is not.",
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
            failures.append(
                f"DORMANT: {name} — {n} consumer(s), need >= {floor}  [{pattern} in {path_rel}]"
            )
    return failures


def self_test() -> int:
    """Falsification proof: the scanner MUST flag a guaranteed-dormant sentinel (proves it can go red)
    AND pass a known-wired capability (proves it isn't a blanket false-positive)."""
    sentinel = scan(
        [
            (
                "sentinel (no consumer exists)",
                r"__NEVER_EXISTS_DORMANCY_SENTINEL__",
                "src/cohezion",
                1,
            )
        ]
    )
    if not sentinel:
        print(
            "SELF-TEST FAILED: scanner did NOT flag a guaranteed-dormant sentinel — it cannot go red."
        )
        return 1
    wired = scan([REGISTRY[0]])  # the H1 gate-fires consumer, which is present
    if wired:
        print(f"SELF-TEST FAILED: scanner false-flagged a wired capability: {wired}")
        return 1
    print(
        "SELF-TEST OK: scanner flags the dormant sentinel (red) and passes the wired capability (green)."
    )
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    failures = scan(REGISTRY)
    if failures:
        print("DORMANCY SCAN FAILED — a load-bearing capability lost its production consumer:")
        for f in failures:
            print("  " + f)
        print(
            "\nA capability with no consumer is wired structurally but dead functionally (verification-depth.md)."
        )
        return 1
    print(f"dormancy scan OK — all {len(REGISTRY)} curated capabilities have production consumers.")
    if KNOWN_DORMANT:
        print(
            f"NOTICE — {len(KNOWN_DORMANT)} capability(ies) known-dormant and intentionally unguarded:"
        )
        for d in KNOWN_DORMANT:
            print("  - " + d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
