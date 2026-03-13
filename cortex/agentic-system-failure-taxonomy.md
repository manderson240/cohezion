---
title: "Agentic System Failure Taxonomy"
date: 2026-03-05
tags: [concept, lessons, compound-engineering, evaluation, agentic-ai, anthropic]
status: active
aspect: knower
neural:
  activation: 0.95
  stage: growing
  synapse_in: 2
  synapse_out: 8
---

# Agentic System Failure Taxonomy

A taxonomy of failure modes observed across 60+ compound engineering sessions, derived from 45 operational lessons. These are not theoretical — each category is grounded in specific incidents where the system broke and had to be repaired.

This taxonomy is the empirical complement to the theoretical agentic AI literature. Where papers describe what agents *should* do, this corpus documents what they *actually* do wrong, at what cost, and how to prevent it.

---

## Category 1: Context and Memory Failures

The most expensive category. When an agent loses or misreads its context, it re-does completed work, corrupts state, or acts on stale assumptions. Estimated cost per incident: 30-90 minutes of session loss.

**Lessons in this category:**
- `lesson-01` — Agent output exists in files the agent can't auto-read; context that isn't actively loaded doesn't exist for the agent
- `lesson-07` — GTT carveout illusion: agent assumed 512MB GPU memory carveout was a hard limit; actual usable pool was 128GB. False environmental model caused 2 wasted sessions
- `lesson-19` — Session awareness protocol: without explicitly loading prior session state, agents repeat decisions already made. Context injection from vault eliminates 30-60 min re-orientation
- `lesson-37` — Experience-guided execution: reading 5 prior session notes before starting work reduced re-orientation overhead by measured 40%
- `lesson-39` — Vault audit must exclude worktrees: including worktree directories in vault scans produces false positives on every health metric
- `lesson-40` — Sequential numbering offset: when lesson indexes drift from file counts, downstream index corruption propagates silently

**Pattern:** Context failures compound. An agent that starts with wrong context makes wrong decisions that produce wrong state that the next session inherits.

---

## Category 2: Infrastructure Reliability Failures

Failures in the substrate — databases, model servers, test runners, CI pipelines. These block all other work until resolved.

**Lessons in this category:**
- `lesson-05` — SurrealDB schema: type mismatches fail silently at write time, surface as corrupt reads later. Schema must be validated end-to-end before data ingestion
- `lesson-06` — Ollama latency: local model inference adds 200-800ms per call; synchronous calls in tight loops produce cascading timeouts
- `lesson-10` — GitLab CI runner: self-hosted runners require explicit tag configuration; untagged jobs queue indefinitely without error
- `lesson-15` — System lockup 2026-01-27: concurrent writes to shared mutable state caused full system lockup requiring hard restart; asyncio lock isolation was the fix
- `lesson-21` — Runtime JSON pollution: logging to stdout in library code corrupted JSON being parsed by callers; separation of log channels is mandatory
- `lesson-25` — uv venv contention: parallel sessions sharing a virtual environment produced silent dependency conflicts
- `lesson-32` — Concurrent pytest contention: parallel test workers sharing a singleton service produced intermittent failures. Fix: singleton reset between tests via `ServiceClass.reset()` in fixtures
- `lesson-34` — Test hang from unmocked live service: a test that forgot to mock an external service call hung indefinitely when the service was slow; all external calls in tests must be mocked
- `lesson-36` — MCP configuration requires end-to-end test: MCP server config errors are invisible until a client actually calls a tool; unit tests on server alone are insufficient

**Pattern:** Infrastructure failures are often silent — they produce wrong results rather than errors. End-to-end testing is the only reliable detection method.

---

## Category 3: Git and Code Integrity Failures

Version control failures that produce state divergence, lost work, or corrupted history.

**Lessons in this category:**
- `lesson-02` — Ruff auto-formats on save: editing a file that ruff immediately reformats causes edit-reformat loops; always re-read files after any auto-formatter touch
- `lesson-09` — Ruff hook fights: pre-commit ruff hook and in-editor ruff conflict on rule sets; one source of truth required
- `lesson-16` — Pre-commit hooks stage override: `git commit --no-verify` bypasses all hooks; legitimate for emergencies, catastrophic if habitual
- `lesson-17` — Stale branch mining: working from a branch 20+ commits behind main produces merge conflicts at the worst possible time; always rebase before starting work
- `lesson-22` — gitignore ordering: later rules override earlier rules; `.gitignore` order is load-bearing
- `lesson-23` — Stash branch switch hazard: `git stash pop` after branch switch applies stash to wrong branch silently
- `lesson-27` — Hook file revert: pre-commit hooks that modify files revert those files to pre-commit state unless the modified files are re-staged before commit
- `lesson-git-worktrees` — Multi-session isolation: without git worktrees, parallel sessions produce merge conflicts. Worktrees eliminate this; each session has isolated state

**Pattern:** Git failures are often discovered late — the corruption happened sessions ago, and the cost is paid during the next attempted merge or push.

---

## Category 4: Agent Execution Discipline Failures

Failures in how agents execute tasks — too broadly, too destructively, without sufficient verification.

**Lessons in this category:**
- `lesson-03` — Critical operations require explicit verification before proceeding; assume nothing about prior state
- `lesson-04` — Surgery lesson: modify only what is required. Broad refactors introduce regressions in code that didn't need to change
- `lesson-08` — Import graph: circular imports in Python fail at import time with cryptic errors; map import graph before adding new dependencies
- `lesson-11` — Team agent efficiency: agents working in parallel without explicit task delineation duplicate work. Delineate by file/module, not by phase
- `lesson-20` — CI scope discipline: CI that runs the full test suite on every commit is too slow to be useful; scope CI to changed modules
- `lesson-28` — Non-critical tracking pattern: logging non-critical failures to a dead-letter queue rather than raising them keeps the primary execution path clean
- `lesson-33` — Skill keyword matching is broad: skill trigger keywords match more situations than intended; agents invoke skills in irrelevant contexts
- `lesson-38` — Singleton executor for sessions: creating a new executor instance per task produces resource leaks; one singleton executor per session is the correct pattern

**Pattern:** Agents optimizing for task completion (not minimal footprint) tend to touch more than necessary, creating collateral damage that subsequent sessions must diagnose.

---

## Category 5: Measurement and Honesty Failures

Failures where the system produced metrics that looked good but measured the wrong thing — or where reporting was optimistic rather than accurate.

**Lessons in this category:**
- `lesson-12` — Layered validation: validating at one layer (unit tests pass) doesn't imply validation at a higher layer (integration fails). Validate at every layer before claiming success
- `lesson-30` — Holographic projection fallback: when full-fidelity data is unavailable, lower-dimensional projections are useful approximations — but must be labeled as approximations, not presented as ground truth
- `lesson-31` — Operation-specific modulation: aggregate metrics hide per-operation variance; a system with average latency 200ms might have P99 latency 2000ms
- `lesson-35` — Non-blocking observability: synchronous telemetry stalls the primary execution path; observability must never be on the critical path
- `lesson-measurement-integrity` — Honest reporting: reporting 98% test pass rate when 2% are known failures is misleading. Accurate status enables accurate decisions
- `lesson-adversarial-review` — Adversarial review before execution: internal review of plans catches 90% of obvious failures before any code is written. 45x ROI on a 10-minute review investment

**The FLUME measurement case:** Hash-based 12D trajectory encoding produced metrics that looked valid (positions were deterministic, trajectories were smooth) but measured nothing semantically meaningful. The failure was only discovered by visualizing trajectory geometry and noticing random-walk structure. This is the canonical measurement failure in the corpus.

**Pattern:** Measurement failures are the hardest to catch because they don't produce errors — they produce plausible-looking wrong answers.

---

## Category 6: System-Level Incidents

High-cost incidents that affected the entire system, not just one component. Each required multi-session recovery.

**Incidents:**
- `lesson-13` — **8.6M file incident:** An unconstrained file generation loop produced 8.6 million small files, filling the filesystem and causing system lockup. Recovery: 3 sessions, filesystem repair, pre-commit enforcement. Root cause: no upper bound on generative output without explicit constraint
- `lesson-15` — **System lockup 2026-01-27:** Concurrent asyncio writes to shared mutable state caused deadlock. Recovery: hard restart, asyncio lock isolation, singleton pattern enforcement
- `lesson-adversarial-review` — **Integration theater detection:** System appeared to be working end-to-end; adversarial review revealed key components were mocked in ways that masked real integration failures. Recovery: explicit end-to-end tests for every integration point

**Pattern:** System-level incidents share a common cause — an unchecked assumption that the system would self-limit. It doesn't. Explicit bounds, explicit locks, explicit integration tests.

---

## What This Corpus Demonstrates

Most research portfolios show what was built. This one shows what was broken, documented as it was breaking, and fixed. The 45 lessons represent empirical evidence of a specific kind of systems thinking: the willingness to document failures with the same rigor as successes, and to derive reusable patterns from them.

The taxonomy above is not exhaustive — it's a first-pass grouping to make the corpus navigable. A more rigorous analysis would quantify cost per category, identify cross-category failure chains, and test whether the lessons actually prevent recurrence in new sessions.

That analysis would be a research contribution. The corpus that enables it already exists.

---

## Related

- [[compound-engineering]] — the methodology that makes this corpus possible
- [[lesson-measurement-integrity-honest-reporting]] — the honesty principle underlying the corpus
- [[lesson-adversarial-review-before-execution]] — the adversarial review pattern derived from Category 6
- [[FLUME-Architecture]] — the FLUME measurement failure is the canonical Category 5 case
- [[2026-03-03-vault-hidden-contributions-assessment]] — identified the lessons corpus as the vault's most undervalued asset
- [[agent-journey-tracking]] — the observability system that makes Category 2 failures visible
- [[non-blocking-observability]] — the pattern derived from Category 5 telemetry failures
- [[multi-session-compound-engineering-workflow]] — the pattern derived from Category 3 git failures
