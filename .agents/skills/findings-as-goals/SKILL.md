---
name: findings-as-goals
description: |
  Turn one-off analysis results (a README of findings, a report, a write-up) into goals with
  deterministic acceptance criteria that re-check themselves, using
  cohezion.compound.goals_and_loops_orchestrator. Use when: (1) findings were produced once by a
  script and then written down by hand, (2) an adversarial review produced fixes you do not want to
  drift back, (3) the user asks to "refactor traces into loops and goals" or make results
  "self-verifying", (4) prose figures must keep matching committed JSON outputs. Key insight: a
  written claim is a linear trace; a goal recomputes it on every run, and review findings belong
  in the goal as standing criteria, not in a commit message.
author: Claude Code
version: 1.0.0
source: session 2026-11-04 (research/artemis2/study_goals.py; 7 goals, 14 criteria)
---

# Findings as Goals

## Which framework

Cohezion has two "trace into loops" modules. Use the light one:

| Module | Import cost | Fits |
|---|---|---|
| `cohezion.compound.goals_and_loops_orchestrator` | ~0.08 s, no torch | Goals with many deterministic acceptance criteria; execute -> verify -> fix loops |
| `cohezion.flume.loop_goal_refactor_engine` | ~6 s, imports torch via `cohezion.flume` | Event-log traces (SECURITY_VIOLATION, AGENT_COMPLETE...) -> one metric goal; SurrealDB persistence |

Measure with `python -X importtime -c "import <module>"` before choosing.

## Pattern

```python
orch = GoalsAndLoopsOrchestrator()
goal = orch.create_goal(gid, title, objective, [(cid, desc) for cid, desc, _fn in checks])
loop = orch.create_loop(gid, max_cycles=2)
state = {}
async def exec_fn():   state["study"] = Study()          # FRESH cache each cycle: recompute
async def verify_fn():
    for ac in goal.acceptance_criteria:
        try:    ac.verified, ac.evidence = fns[ac.id](state["study"])
        except Exception as exc: ac.verified, ac.evidence = False, f"{type(exc).__name__}: {exc}"
    return goal.is_converged(), summary
await loop.run(exec_fn, verify_fn)
```

- **One goal per group of findings**, with criteria that each return `(bool, evidence)`. Evidence
  is the measured value, not "ok", so the output file shows *why*.
- **Criteria recompute from inputs** where affordable (re-run the analysis, diff against the
  committed JSON). Where not, they check the committed output against the claim.
- **Cycles retry transient failures only** (a network fetch). Never edit a reference value
  inside a cycle to make a check pass.
- **Note the orchestrator gap:** `ExecutionLoop.run` marks SATISFIED from `verify_fn`'s boolean,
  not from the criteria. Return `goal.is_converged()` so the two cannot disagree.

## What to make into criteria

1. **Reproduction:** rerunning the analysis gives the committed output exactly (or field-equal).
2. **Each headline claim:** the number or relation the prose asserts, checked against the data.
3. **Each accepted review finding** as a standing check. Example: the far-side result was
   qualified for rotation, so the qualification itself became criterion F4.
4. **Independent-source agreement:** when one source replaced another (SPICE for Horizons),
   record the difference and require it below tolerance.
5. **A write-up register:** `(phrase that must appear in README, check that the JSON supports it)`.
   It fails if the prose drifts OR the data changes. That catches the fact-checker's class of
   error permanently.
6. **Inputs pinned:** hash every input file into the result, so a pass names the data it saw.
7. **Regressions:** the test suite for past fixes passes (subprocess pytest).

## Gotchas

- **The loop's first run will catch bugs in your criteria.** Here it found one reading a field
  with the wrong shape and one treating a list as a count. Expect this; it is the point.
- **A partial run must not overwrite the committed full result.** `--skip-network` once replaced
  every network goal with "skipped" in the committed JSON. Write the default output only on full
  runs.
- **Tests must break the claim, not the code.** For each criterion, a test that monkeypatches the
  committed data into a violating state and asserts FAIL with the bad value in the evidence.
- Keep the evidence strings free of timings if the JSON is committed, or accept noisy diffs.

## Reference implementation

`research/artemis2/study_goals.py`, `research/artemis2/study_goals.json`,
`tests/unit/research/test_artemis2_study_goals.py`.
