# Hackathon Delegation — Goals & Autonomous Loop Spec

Drives the coordinator loop that advances the competition/hackathon portfolio on **local
inference** (AMD fleet, $0). Each entry has a **verifiable goal** so the loop converges
instead of spinning. The loop reads this file each cycle, picks the highest-priority entry
with an UNMET goal and the nearest deadline, does ONE increment, verifies, updates the
`progress` line, and reports.

## Hard rules for the loop (every cycle)
1. **Coordinate first.** Check `GET :13305/api/v1/health` and the session bus
   (`session_message` / Telegram `@CohezionBot`). If a peer session is actively using the GPU,
   SKIP GPU work this cycle — report status only.
2. **Local inference only** for LLM work — route through the hardened
   `shared/cohezion_bridge.py::complete_with_fallback` / `complete_omni` (already-loaded omni
   models; $0). Cloud only if a quality gate fails, and say so.
3. **Non-destructive + provenance.** No deletes; our-own work only. **No git commit/push
   without explicit user approval.**
4. **Report** a 2-line status to `@CohezionBot` each cycle (advanced what / blocked on what).
5. **Verify before claiming done.** A packaging/import error reads identically to "it failed" —
   confirm the artifact actually ran.
6. **Harness gate (autoharness).** Any increment that touches code MUST pass
   `bash scripts/ci/check_labs_router_only.sh` (router-only :13305 invariant) AND an
   `ast.parse` compile-check on every touched file BEFORE you update `progress:`. On RED,
   revert the increment this cycle — a regression is not progress.
7. **Stay lean (autocontext).** Delegate research/synthesis to `gaia_local.delegate`; write
   findings to files, not the chat. Heavy reasoning goes to local inference, not your context.
8. **Goals are bmad acceptance criteria.** An entry is DONE only when its `AC:` command runs
   green — not when the code "looks wired". If an entry lacks an `AC:` line, add a testable one
   before working it.

## Portfolio (priority by deadline)

### Nemotron — `nvidia-nemotron-model-reasoning-challenge` — DUE Jun 15 (TODAY)
- **Goal:** submission `53720998` reaches a terminal score; if > 0.84 it banks, else 0.84 floor holds; log outcome.
- **State:** DONE. Submission `53720998` scored **0.78** (< banked v9 0.84). Floor held; Kaggle
  keeps best → **final 0.84**. No productive resubmission remains. **No further work.**
- `progress:` CLOSED — final 0.84 (v9 banked); sftinit 0.78 did not improve.

### band-of-agents — Band of Agents Hackathon — DUE Jun 19
- **Goal (verifiable):** `demo/run_demo.py` completes end-to-end with all 3 agents posting to
  Band, and the run reports a **local** generation backend (Gemma-4-E4B / loaded omni) for the
  parts where local quality suffices — i.e. "$0/loop" is *true*, not a reachability probe.
- **Increment path:** wire each agent's generation through `bridge.complete_with_fallback(...,
  cloud_fn=<anthropic>)` behind `COHEZION_LOCAL_FIRST`; set the backend metric from the returned
  `backend`. Keep structured-codegen on cloud if local JSON quality is insufficient (task-routing).
- `AC:` `cd band-of-agents && COHEZION_LOCAL_FIRST=1 python demo/run_demo.py` exits 0 AND the
  run log shows `generation_backend` in {Gemma-4-E4B-it-GGUF, <omni-model-id>} for ≥1 agent
  (i.e. local silicon actually served it), not "cloud"/reachability-probe.
- `progress:` bridge primitives added (complete_with_fallback + complete_omni); agent wiring + honesty-metric PENDING.

### uipath-maestro — UiPath AgentHack — DUE Jun 29
- **Goal:** Maestro-case flow runs end-to-end; honest backend attribution (no `cpu_tier_used`
  from a reachability probe).
- `AC:` `cd uipath-maestro && python -m agents.orchestrator_agent --selftest` (or the demo entry)
  exits 0 AND emits `generation_backend` reflecting the model that actually served — never a
  literal `cpu_tier_used` flag derived from a `is_available()` probe.
- `progress:` bridge primitives added; agent wiring PENDING.

### slack-cohezion-agent — Slack Agent Builder Challenge — DUE Jul 13 (REVENUE: prize competition)
- **RECOVERED 2026-06-16.** This is a PRIZE HACKATHON, not a personal tool — the user doesn't use
  Slack personally, but winning the competition is a revenue opportunity. Keep it in scope.
- **Goal (verifiable):** `/cohezion ask|review|search` run on the live fleet at $0; upgrade
  `ask_handler` single-tier call to full NPU→omni escalation, and add `complete_omni` vision so
  image messages are handled locally (a differentiator for the MCP-server track).
- `AC:` `cd slack-cohezion-agent && python -c "from handlers.ask_handler import handle_ask; print(handle_ask('explain HIHO'))"`
  returns a non-empty answer with a local `backend`, AND `status_handler` reports all tiers on :13305.
- `progress:` bridge primitives added; ask_handler already honest/local-first; escalation+omni upgrade PENDING.

### Kaggriculture — Google AI Agents capstone — opens ~Jun 19
- **Goal:** when the capstone opens, ship a standalone `submission.py` agent (per
  `kaggle-simulations-agent-submission` skill): per-tick timeout + heuristic fallback; optional
  local-inference with degrade-to-heuristic when GPU/network absent.
- `progress:` not open yet — monitor enrollment/capstone availability.

### AGI-Golf — `neurogolf-2026` — DUE Jul 15
- **Goal:** confirm baseline kernel score, then iterate. NOTE: Kaggle GPU **notebook** comp — runs
  on Kaggle infra, NOT local inference. The loop tracks/iterates but inference is remote.
- `progress:` baseline kernel queued (see AGI_GOLF_STATUS.md).

### ARC Prize tracks — DUE Nov 2 / Nov 9
- **Goal:** deferred until the nearer-deadline work is banked. Not started.
- `progress:` deferred.
