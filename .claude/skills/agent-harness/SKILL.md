---
name: agent-harness
description: |
  The shared operating harness every Cohezion sub-agent inherits: how to load context,
  reach memory, run the BMAD Dev->QA separation, and close the experiential-learning loop.
  Use when: (1) you are a spawned sub-agent starting a task, (2) you are about to report a
  finding or claim something is done, (3) you are building or revising an agent definition.
  Audited 2026-08-08: LEARNING present in 4/21 agents, MEMORY in 8/21 — this skill exists so
  those are inherited once rather than copy-pasted 21 times.
author: Claude Code
version: 1.0.0
---

# Agent Harness

A 24-line agent definition with a tools list is a *role label*, not a harness. This is the
operating procedure that turns one into the other. Reference it from an agent's definition
rather than restating it.

## 1. Bootstrap — load context BEFORE working

Do these in one batch, not serially:

1. **Repo context** — root `CLAUDE.md`, plus the nearest subdirectory `CLAUDE.md` for the
   package you are touching (they auto-load, but know what they said).
2. **Invariants** — `.claude/rules/harness.md` for the series governing your area
   (CB/GIC/W/HR/...). If your change touches a documented invariant, that invariant is your
   acceptance criterion.
3. **Prior art** — `vault_find_relevant_context(<task>)` before deriving anything. The vault
   holds 150+ decisions; re-deriving one is pure waste.
4. **Peer state** — read the datamesh bus for recent peer posts. The bus is write-only unless
   someone reads it; a peer may have solved your exact problem hours ago.

Cost: one batched round-trip. Skipping it is how the same bug gets fixed twice.

## 2. Tools — discovery over assumption

- Deferred tools must be loaded before use: `ToolSearch(query="select:Name1,Name2")` in ONE
  call listing everything you expect to need. Never one call per tool.
- Prefer the dedicated file/search tools over shell equivalents.
- On the FIRST read-only or permission-denied error, **stop and reroute** — do not retry the
  blocked path. Retrying a read-only mount always fails.

## 3. Memory — read it, and write back

- **Read**: `vault_find_relevant_context`, `graph_search`, SurrealDB (`ns=cohezion`, `db=main`).
- **Write**: a decision worth keeping goes to the vault (`vault_log_decision`), not into your
  final message where it dies with your context.
- Treat recalled memory as **point-in-time**. If it names a file, flag, or function, verify the
  thing still exists before relying on it. Memories go stale; the code is ground truth.

## 4. BMAD Dev -> QA separation (MANDATORY for load-bearing work)

**The agent that BUILDS must not be the agent that SIGNS OFF.** A producer's
"all green, verified" is a *claim*, not QA — it re-creates the author-test correlation that
lets a whole class of defect ship green.

- **Dev lane** produces the artifact and states explicit acceptance criteria.
- **QA lane** is a *different* agent with *fresh context*, instructed to assume the work is
  broken, that independently EXECUTES the falsification. A read-only reviewer can reason but
  cannot run the proof — the verifier needs execution tools.
- Disagreement escalates ONE tier locally. It does not go to cloud (see
  `quarter-on-a-string-protocol`).

Relevant BMAD skills: `bmad-agent-dev`, `bmad-code-review`, `bmad-check-implementation-readiness`,
`bmad-correct-course`, `bmad-retrospective`.

## 5. Verification — test the CLAIM, not the component

Before reporting anything as done:

- State the claim in one sentence, then run the command that would **falsify** it.
- **Consumption, not declaration.** A capability is not wired because a kwarg is accepted or a
  symbol exists. Grep for a non-test, non-`def` consumer. No consumer = dormant.
- **Prove the check can FAIL.** A gate you have never seen reject anything is not a gate. Run
  it against a known-bad input first.
- **Silence is not success.** HTTP 200, `ok=True`, and a plausible length can all accompany
  garbage — verified 2026-08-08, when a lane returned 8,889 chars of one repeated trigram with
  every surface signal green. Gate model output on CONTENT.
- A negative result from an unvalidated instrument is **UNKNOWN**, not ABSENT. Run a control
  that must succeed before recording any "not found".

## 6. Report honestly

- Report actual numbers. "2,675/2,700 (98.1%)" beats a rounded-up claim, because the real number
  is what the next decision is made on.
- Separate **verified** from **inferred** from **assumed**, explicitly.
- Say what you did NOT do. An "Honest limits" section is not padding; it is what stops the next
  agent from trusting coverage you never had.
- If findings are mostly false positives, say so and file ONE honest card rather than N noisy
  ones. Filing noise spends human triage, which is the scarcest resource in the loop.

## 7. Close the loop — experiential learning

This is the step 17/21 agents currently skip.

On finishing non-trivial work:

1. **Extract** — if the work produced a reusable, non-obvious, *verified* pattern, invoke
   `Skill(learn)`. Let it judge; silence is a valid outcome. Check for an existing skill first
   and refine it (bump version) rather than duplicating.
2. **Persist** — update the layer that auto-loads for this work (the relevant
   `.claude/rules/*.md`, a vault decision, or the module's status doc). A lesson that lives only
   in a transcript is lost.
3. **Publish** — post a short result to the datamesh bus so peers see it mid-flight rather than
   rediscovering it.
4. **File follow-ups** — an unfinished thread becomes a work-queue card, not a good intention.
   To be picked up it needs a `(type, relevance, status)` triple a consumer actually queries —
   see `work_queue_router.py` and `compound_feeder.py`; the wrong triple means nothing reads it.

## Anti-patterns

- Reporting "done" without having run the falsifying command in *this* turn.
- Self-certifying your own build instead of routing it to an independent QA lane.
- Escalating to cloud without a genuine local quality-gate failure.
- Filing N low-confidence findings because the volume looks like productivity.
- Treating a recalled memory as current state without verifying it against the code.
