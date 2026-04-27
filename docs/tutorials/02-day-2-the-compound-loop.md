---
title: "Day 2 — The Eleven-Step Compound Loop"
target_audience: contributor with one local commit, no executor knowledge
estimated_time: 2-3 hours
prerequisites:
  - Tutorial 1 completed (working install, single test runs green)
  - Comfortable reading Python (no PyTorch knowledge required)
prior_tutorials: [01-day-1-setup-and-first-test.md]
next_tutorial: 03-day-3-skills-and-vault.md
related_adrs: [ADR-001-eleven-step-compound-loop.md]
---

# Day 2 — The Eleven-Step Compound Loop

Today you read the file you edited the docstring of yesterday. Specifically: `src/cohezion/compound/executor.py`. Cohezion has many subsystems — FLUME VAE, the cosmogonic autonomy ladder, the SwarmEnv multi-agent coupling — but `CompoundExecutor.execute_task()` is the spine. Every other subsystem either feeds into it (the vault, the skill registry, the cost router) or attaches to it (the journey tracker, the metrics aggregator, the alignment analyzer, the degradation detector).

The architectural decision behind this file is recorded in [ADR-001](../adrs/ADR-001-eleven-step-compound-loop.md). Read that ADR briefly first — five minutes — then come back. The short version: the loop's eleven core steps are a *fixed-order architectural invariant*, not a coding pattern. The fixed order is what allows downstream consumers (vault search, metrics aggregator, journey tracker, skill refiner) to assume their inputs exist. That is the structural reason "compound effects" accumulate.

## What you will do today

1. Read the project's `CLAUDE.md` "The Compound Engineering Loop (Production-Ready)" section (about half a page).
2. Open `src/cohezion/compound/executor.py` in your editor and locate the eleven `# Step N` comment markers in `execute_task()`.
3. Annotate each step in your editor with a one-line note describing what it does. (For yourself; do not commit these notes.)
4. Trace one execution end-to-end by adding a `print()` at each step boundary and running a single test.
5. Read the journey-tracker output and understand what a "12-D position" actually contains.
6. Remove the prints and run the same test cleanly.

By the end you will be able to answer three questions without looking: which steps are *learning* steps, which are *diagnostics* steps, and which are optional.

## Step A — Read the canonical overview

Open `CLAUDE.md` in the repository root. Find the section titled **"The Compound Engineering Loop (Production-Ready)"**. It contains an ASCII diagram that lists the eleven phases. The diagram is the truth source; the ADR is the rationale; the executor is the implementation. Hold all three in your head simultaneously.

> **Why this matters.** `CLAUDE.md` is the project's single most important document for new contributors. It is approximately 26 KB. Read it linearly once, then use it as a lookup. The PRFAQ exercise (`research/prfaq/2026-04-23-cohezion-prfaq.md`) lists "a 5-minute getting-started experience" as a missing capability — meaning right now the bring-up genuinely *requires* reading `CLAUDE.md`. Your investment of one careful read pays dividends in every subsequent day of work.

## Step B — Locate the eleven step markers

In your shell:

```bash
grep -nE "# Step [0-9]+(\.[0-9]+)?:" src/cohezion/compound/executor.py
```

You will see roughly two dozen matches. The eleven *core* steps appear with single-digit numbers (`# Step 1:`, `# Step 2:`, ..., `# Step 10:`). The matches with decimal numbers (`# Step 1.3:`, `# Step 5.5:`, `# Step 7.6:`, `# Step 10.5:`) are the *optional sub-steps* — collaborators that attach at step boundaries without changing the core ordering. ADR-001 identifies this distinction explicitly: optional sub-steps "accumulate, drifting toward an effective 15-step loop without that being explicit." Be aware of the drift; do not let it confuse the ordering of the core eleven.

The eleven core steps in `execute_task()` (line numbers reflect the post-Wave 2D state in the synthetic-sniffing-panda worktree; they may shift slightly):

| # | Marker | What it does | Arc |
|---|---|---|---|
| 1 | `# Step 1: Get experience guidance` | Queries the vault for prior similar runs, returns guidance dict. | learning (read) |
| 2 | `# Step 2: Log execution start` | Stamps the trajectory record. | observability |
| 3 | `# Step 3: Check input via guardrails` | Runs the input through `GuardrailPipeline`; can refuse the task. | safety |
| 4 | `# Step 4: Log execution results` | Records output, success, metrics into the trajectory. | observability |
| 5 | `# Step 5: Detect anomalies (non-blocking)` | Runs `InflectionDetector` to flag unusual outcomes. | diagnostics |
| 6 | `# Step 6: If successful, extract patterns` | Calls `RetrospectionEngine.extract_patterns()` on the trajectory. | learning (write) |
| 7 | `# Step 7: Refine skills based on execution results` | Calls `SkillRefiner.refine()` *gated* by retrospection. | learning (write) |
| 8 | `# Step 8: Record metrics (non-blocking)` | Sends per-execution metrics to `GlobalMetricsAggregator`. | diagnostics |
| 9 | `# Step 9: Track journey (non-blocking)` | Updates the agent's 12-D position via `JourneyTracker`. | diagnostics |
| 10 | `# Step 10: Complete universe journey (non-blocking)` | Closes out the universe-bridge journey if one is open. | diagnostics |
| 11 | (implicit completion / ExecutionResult return) | Returns the typed `ExecutionResult` to the caller. | observability |

Two notes on this table.

First, "Step 11" as the closing return is a reading of how the loop terminates; some readers prefer to count step 10 plus the optional sub-steps (10.5 Ouroboros, 10.6 Mycelium) as filling the eleventh slot. The ADR is explicit that the *invariant* is the fixed order; the exact arithmetic is less load-bearing than the structure. Pick whichever count makes sense to you and move on.

Second, the **skill-refinement step is gated by retrospection**: step 6 must produce a non-trivial pattern set before step 7's `SkillRefiner.refine()` will commit anything. This is the safety design — a single noisy execution does not silently mutate skills. ADR-001 puts it: "learning is allowed to be slow and gated, diagnostics must be cheap and unconditional."

## Step C — Annotate each step in your editor

Open `src/cohezion/compound/executor.py` and scroll to `def execute_task(...)` (around line 307). For each `# Step N:` marker, add a comment on the next line summarizing what *you* think the step does. Example:

```python
        # Step 5: Detect anomalies (non-blocking)
        # — runs InflectionDetector on the just-completed trajectory.
        #   non-blocking: failure here does not abort the execution.
        if self._inflection_detector and not self._degradation_mode:
            ...
```

Do this for all eleven core steps. The exercise is for *your* understanding; you will not commit these annotations. The point is to force yourself to read the actual code in each block instead of trusting the marker comment.

> **Why this matters.** The marker comments are a contract: ADR-001 specifies that the per-step `# Step N` markers are part of the loop's invariant and a static-check verification (`grep -nE "# Step [0-9]" src/cohezion/compound/executor.py | wc -l` should yield ≥ 11). When a refactor moves code, the marker must move with it. Knowing what the marker promises — and what the underlying code actually does — is the prerequisite for any future change to this file.

## Step D — Trace one execution end-to-end

Now you will run the loop and observe each step fire. The cleanest way to do this without setting up a vault, a SurrealDB, an LLM, or any of the optional collaborators is to use the existing test fixtures.

Open `tests/compound/test_executor.py` (or one of its siblings; the file list under `tests/compound/` is in `tests/conftest.py`'s `reset_singletons` documentation). Look for a test named something like `test_execute_task_returns_result`. If you cannot find an obvious one, use the comprehensive test:

```bash
uv run pytest tests/compound/test_executor_comprehensive.py -q -k "execute" --tb=short 2>&1 | head -40
```

The `-k` filter narrows to tests with "execute" in the name, and `--tb=short` keeps the failure output bounded if anything errors. You should see passes.

Now temporarily add a `print()` inside `execute_task()` at each step boundary. Your edit will look like:

```python
        # Step 1: Get experience guidance (enhanced with trajectory search)
        print(">>> step 1: experience guidance")
        guidance = self.get_experience_guidance(task_description, project, operation_type)
```

Repeat for steps 2 through 10. Save the file. Re-run the same test with stdout capture disabled:

```bash
uv run pytest tests/compound/test_executor_comprehensive.py -q -k "execute" -s 2>&1 | grep ">>>" | head -30
```

The `-s` flag is the one project exception to "always use `-q`": it disables pytest's stdout capture so your `print()` statements actually appear. The `grep ">>>" | head -30` keeps the output bounded.

> **Checkpoint.** You should see the `>>>` markers fire in order: 1, 2, 3, 4, 5, 6 (or skipped if guardrails or success conditions short-circuit), 7, 8, 9, 10. If you see steps out of order, you are looking at the wrong execution path; the test is exercising a code branch that early-returns. Try a different test, or open the executor and trace the conditional that caused the skip.

The classic short-circuit happens at **Step 1.3 (template matching)**. Before the eleven core steps even begin, the executor checks for a high-similarity match in the template cache. On a hit, it returns immediately:

```python
        if template_match is not None:
            ...
            return ExecutionResult(
                success=True,
                output=template_match["response"],
                metrics={"template_match": True, ...},
                ...
            )
```

This is the *semantic-cache short-circuit* — the same mechanism the project's PRFAQ describes as a "95%+ L2 cache hit rate" claim. (The PRFAQ also notes this number is from the SemanticCache test suite's narrow benchmark, not production traffic; do not over-claim it.) On a cache hit, none of steps 1.5 through 10 run. That is the design: when the answer is already known, the cheapest correct response is "return it."

## Step E — Read the journey-tracker output

Step 9 calls `JourneyTracker.track_execution()` and the result is a "12-D point" — a position in the project's twelve-dimensional latent state space. Where do those twelve dimensions come from? They are the project's choice of agent state representation, codified in `src/cohezion/compound/journey_tracker.py`:

```bash
grep -n "AXIOMATIC_DIMS" src/cohezion/compound/journey_tracker.py
```

You will see `AXIOMATIC_DIMS = 12` somewhere around line 105. The tracker's `track_execution()` method computes a position from the most recent execution's outcome features (success, duration, token usage, alignment score, coherence, etc.) and appends it to the running journey.

To see one trajectory, augment your `print()` at step 9 to dump the point's `coherence` and `efficiency`:

```python
        # Step 9: Track journey (non-blocking)
        print(">>> step 9: journey tracking")
        if self._journey_tracker:
            try:
                ...
                point = self._journey_tracker.track_execution(...)
                if point:
                    print(f">>> step 9: coherence={point.coherence:.3f} efficiency={point.efficiency:.3f}")
```

Re-run the same test with `-s` and inspect the output. Coherence ≈ 0.5 is the HIHO attractor — the safe equilibrium the cosmogonic autonomy ladder gates promotion against. ADR-001 marks this threshold as "empirical and lives outside this ADR"; the journey tracker simply records whatever value the metric computation produces.

> **Why this matters.** The 12-D position is the addressable surface that *every other Cohezion subsystem* reads: the cosmogonic autonomy ladder reads it for promotion/demotion decisions, the FLUME VAE encodes it into the 256-D semantic latent, the dashboard's `/genesis` route renders it via Three.js. If you ever need to debug "why did agent X get demoted?", the answer is in the journey tracker's recent points.

## Step F — Read the metrics-aggregator output

Step 8 sends per-execution metrics to `GlobalMetricsAggregator`. The aggregator does not log to stdout by default; it accumulates by skill, agent, tier, and time-window. To peek at it from a Python REPL after running a test:

```bash
uv run python -c "
from cohezion.compound.global_metrics_aggregator import GlobalMetricsAggregator
g = GlobalMetricsAggregator.get_default() if hasattr(GlobalMetricsAggregator, 'get_default') else None
if g:
    print(g.get_metrics_snapshot() if hasattr(g, 'get_metrics_snapshot') else 'no snapshot api')
else:
    print('no default singleton — aggregator must be injected at construction time')
"
```

The aggregator might or might not have a default singleton in your local env — collaborators are *injected* into the executor's constructor, and the test fixtures often pass `None`. ADR-001 calls this out explicitly: "Every collaborator slot in the constructor is `Any | None`, and the per-step blocks check for the collaborator before invoking." This is the dependency-injection contract. It is also why your `print()` at step 8 may or may not see the metrics actually fire — depending on the test, the collaborator may be absent.

## Step G — Remove your prints and re-verify

Once you have a mental model of the loop, undo your `print()` statements:

```bash
git diff src/cohezion/compound/executor.py
git checkout src/cohezion/compound/executor.py    # if you only added prints
```

If you want to keep your annotation comments from Step C, you can preserve them and only revert the `print()` lines. Either way, re-run the test you were using:

```bash
uv run pytest tests/compound/test_executor_comprehensive.py -q
```

The pass count should match what it was before you started annotating. If it does not, you accidentally changed behavior — read your diff carefully and back out the offending edit.

## What you just learned

1. **The loop has two arcs and one safety mechanism.** Steps 1, 6, 7 are the *learning arc* — vault read, retrospection, skill refinement. Steps 5, 8, 9, 10 are the *diagnostics arc* — anomalies, metrics, journey, universe completion. Step 3 is the *safety check* — guardrails can refuse the task before any work happens. The split is deliberate: learning is gated and slow; diagnostics are unconditional and cheap.
2. **The fixed order is the architectural invariant.** Steps cannot be reordered without re-defining the contract that downstream consumers (vault, metrics, journey, refiner) read. ADR-001 grades the reversal cost as **HIGH** — 3-5 person-weeks across multiple subsystems. Do not propose changes to this file lightly.
3. **Collaborators are injected and optional.** Every collaborator slot in `CompoundExecutor.__init__` is `Any | None`. Every per-step block guards the collaborator with `if self._foo:`. This is what allows the loop to run in degraded modes (no universe bridge, no metrics aggregator, no skill refiner) while preserving the eleven-step shape.
4. **Template matching short-circuits the loop.** The semantic-cache hit at step 1.3 returns immediately with `tokens_saved` recorded. This is the structural mechanism behind Cohezion's compound-cost story: the more the system runs, the more its history matches the next request, the cheaper that next request becomes.
5. **The 12-D position is addressable state.** Step 9's `JourneyTracker.track_execution()` returns a point with `coherence`, `efficiency`, `phi_score`, and `metadata`. Every other subsystem reads from this; the cosmogonic autonomy ladder gates trust on its stability over time.

## What you will do tomorrow

Tomorrow's tutorial covers **skills** — the markdown-defined behaviors that the executor invokes, the registry that indexes them, and the vault that holds the canonical copies. The skill registry has 235 entries (215 PRIME) in `src/cohezion/skills/skill_registry.json`; the executor's step 7 (`SkillRefiner.refine()`) writes back into that registry over time. Today you saw the loop that *uses* skills; tomorrow you will see the system that *defines* them.

→ Continue to [Tutorial 3 — Day 3: Skills and the Vault](./03-day-3-skills-and-vault.md).

→ Back to [Tutorial 1 — Day 1: Setup and First Test](./01-day-1-setup-and-first-test.md).
