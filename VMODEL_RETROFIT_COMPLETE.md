---
title: "V-Model Retrofit on Polish Campaign"
date: 2026-04-23
campaign: synthetic-sniffing-panda Wave V
---

# Phase A — Regression check

| Phase | Result | Notes |
|---|---|---|
| 1 (inference fleet) | F1-F7 PASS, F8 FAIL | 2 pre-existing pytest failures (`tests/inference/test_registry.py::test_model_entry_is_dataclass_with_expected_fields`, `tests/inference/test_symmetry_bridge.py::test_inject_symmetry_axis_strict_mode_raises_when_bridge_missing`). Not polish-campaign-induced — both predate the campaign branches. 95 pass / 2 fail / 1 warning. F1, F2, F3, F4, F5, F6, F7, F9, F10 all clean. |
| 2 (benchmark) | I0 FAIL | Harness halts at I0 because `benchmarks/fleet_report.md` is absent — that file is produced by `make benchmark-fleet`, which has not been run in this checkout. Not a regression; structural verification cannot proceed without the upstream artifact. |
| 6 (orchestrator) | ALL PASS | 14 pytest cases pass, all orchestrator invariants (O1-O8 + factory + safety + gaia) verified clean. No campaign regression. |

# Phase B — Phase 7 artifact draft

- Plan: `docs/vmodel/PHASE7_POLISH_CAMPAIGN_PLAN.md` (20 invariants P1-P20)
- Harness: `scripts/validation/vmodel/phase7_polish_campaign_harness.py` (342 LOC, structural + tool-based)
- Makefile: `make vmodel-phase1`, `make vmodel-phase2`, `make vmodel-phase6`, `make vmodel-phase7`, `make vmodel-all` added

All three live on branch `polish/vmodel-retrofit` (created from `ffaf26888`) and on the new worktree at `.claude/worktrees/vmodel-retrofit/`.

# Phase C — Harness self-test

Run on `worktree-synthetic-sniffing-panda` (where every campaign artifact is present):

```
[V-MODEL Phase 7 HARNESS] Verifying polish-campaign invariants...
PASS P1: api/__init__.py = 266 LOC <= 400
PASS P2: cohezion_mcp.py = 307 LOC <= 400
PASS P3: api/routes/ has 17 router files
PASS P4: executor_helpers/ has 3 helper files
PASS P5: top-level `import asyncio` present
PASS P6: _validate_identifier helper present
PASS P7: no shell=True in report/server.py
PASS P8: 2 stealth-bare-except violations <= 2
PASS P9: S603/S607 = 0
PASS P10: 968 passing >= 968
PASS P11: 32 tests >= 15
PASS P12: 17 tests >= 10
PASS P13: 1 files / 15 tests
PASS P14: 4 manuscript files
PASS P15: ADR-001..005 + INDEX + TEMPLATE all present
PASS P16: 10 tutorial files
PASS P17: Omega-6 security review present
PASS P18: Omega-12 remediation plan present
PASS P19: 783 mypy errors <= 785
PASS P20: 1022 ruff errors <= 1026

Summary: 20/20 invariants passed, 0 failed.
EXIT: 0
```

**Final result: 20/20 invariants pass on the campaign worktree.**

On `polish/vmodel-retrofit` itself (which is at the bare `main@ffaf26888` parent commit), the harness will fail until PRs #76-#81 merge — that is the intended sequencing.

# Phase D — PR

- Branch: `polish/vmodel-retrofit` (off `ffaf26888`)
- Commit: `1529a92bd feat(vmodel): add Phase 7 — polish-campaign verification harness`
- PR: **#82** — ready for review (not draft), squash auto-merge enabled, currently `MERGEABLE`
- URL: https://github.com/manderson240/cohezion/pull/82

# Limitations

- Harness will fail on `polish/vmodel-retrofit` HEAD until PRs #76-#81 merge (depends on their files for P3, P4, P5-P7, P11-P18)
- Some invariants intentionally LOOSE (e.g., P1 ceiling 400 vs actual 266) so future drift catches at a clear ceiling, not at the current floor
- Coverage % invariants not included (would require `pytest --cov` which is too slow for a phase harness)
- P19 (mypy 785) and P20 (ruff 1026) are tight against today's actuals (783, 1022) — any regression of >2 mypy errors or >4 ruff errors will trip the harness

# Honest assessment

- The polish campaign was NOT run through V-Model formally during execution
- This PR retrofits the contract after-the-fact
- All 20 invariants describe properties the campaign DID achieve, but they were verified by adversarial review (Wave Ω), not by gate harness
- Future polish work should write the V-Model phase plan FIRST, then implement against it
- Phase A regression check found NO polish-induced regressions — the 2 failing inference tests and the absent benchmark artifact predate the campaign and are not in scope
