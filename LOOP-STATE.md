# LOOP-STATE — pending-work drain (Variant D)

Read FIRST every run. Backlog = the session task board's pending items, triaged
by whether an autonomous run can finish them or a gate blocks them.

_Init: 2026-07-17. GOAL: every pending task is done, blocked, or on NEEDS-ME._

## NEEDS ME (user-gated — do NOT attempt autonomously)

| Item | Why it needs you | The ask |
|---|---|---|
| Merge PR #259 | outward + owner-only | `gh auth login --insecure-storage`; retitle; merge (CI red on pre-existing debt → `--admin`) |
| Move-2 graph scale-up (#25) | server restart for lemonade no-think profile — OR run cloud lane (metered, needs budget nod) | complete lemonade 2-profile setup, OR "scale the graph batch" (cloud $) |
| Morning-brief schedule | private-data unattended job + Calendar OAuth | `/mcp` Calendar auth; say "schedule it" |
| RO-mount + gh-auth | privilege / reboot | `sudo umount .git/worktrees` (or reboot); re-auth gh |

## AUTONOMOUS (a run can finish these; each is a Variant-A sub-loop, evidence-checked)

| Item | Status | Note for next run |
|---|---|---|
| #8 lit-sweep deltas remainder (hash-stability probe, difficulty-tiering) | pending | gauntlet-side; low risk; calibration-gate the difficulty tiers |
| #17 Blind-Spots-Bench discrimination probe | pending | pull HF dataset text subset → 3-5 fleet models → spread≥5% test |
| #18 liteparse A/B vs GAIA/pymupdf | pending | needs npx/Node; A/B on 3-4 vault PDFs |
| #23 UniVR process-reward probe | pending | CALIBRATION FIRST (30-70% band) — SEED lesson; else INCONCLUSIVE-INSTRUMENT |
| #27 safe model-swap primitive | **DONE** (loop dogfood, 3 iters) | `load_safety.safe_swap` — transactional, restores prior occupant on load failure/verify-false; never raises; 5 discriminating tests + 29 regressions green. NEXT: wiring it into load_npu callers is a SEPARATE item that goes through the full push-gate (higher ownership tier — it changes live behavior). |
| #36 Move-4 eval-harness consolidation | pending | large; strangler-fig; includes iGPU-lane autoharness |
| #7 vision battery (multimodal) | pending | gemma4-e2b/qwen3vl NPU vision models staged; procedural PIL golds |

## DONE (this session — do not redo)

gauntlet 24/7 · fleet RAM policy · capability index · silicon doctrine · graphify
live-wire · datamesh wire · cockpit UI · ollama_cloud client · 1.1.0 release ·
CI remediation · loop-engineering + ambient-skill + morning-brief skills ·
55+ research verdicts · fail-open-discriminating-test skill.

## SKILLS-&-CAPABILITIES GAP LOOP (2026-07-18, user: "loop until gaps filled")

Analysis: `~/vaults/cohezion-vault/reports/20260718-skills-capabilities-matrix-gap-loop.md`
- **GAP-0 DONE (gated)** — CapabilityMatrix was blind to its own skill catalog
  (loaded 0 skills / 0 agents live). Fixed: `_load_catalog_skills` (96 PRIME
  skills) + repo-root agent path. Adversarial review (2 findings fixed) → 25
  tests green → semver 1.1.0→1.2.0 → **commit 81bc9411** in this clone.
  MERGE = NEEDS-ME (RO-mount + gh-auth): from ~/dev/ci-fix-weaving push branch
  `worktree-dynamic-weaving-wirth` + open/land PR (stacks with the #259 work).
- rung 2 (task #59): consolidate 3 module overlaps — LARGE architectural refactor
  (healing/resilience, eval/evaluation, pipeline/pipelines); integrate-first per
  non-destructive-wiring; deserves its own plan + go before diving in.
- **skill-scoring DONE (gated, task #61)** — catalog skills now carry task-type
  affinity (word-boundary keyword match from concepts) + `run_skill_gap_analysis()`
  (skills assessed apart from models). Live result: 42/96 skills scored; honest
  **skill gap = multilingual (0 skills)**, research thinnest-covered (1). Adversarial
  review (2 findings fixed: vacuous test #4 → model-covered-skill-uncovered discriminator;
  substring→word-boundary matching, dropped ambiguous "language" that masked the
  multilingual gap). 29 tests green → semver 1.2.0→1.3.0 → commit in this clone.
- rung 3 (task #60): progressive-disclosure retrieval probe — measurement, smaller.
- rung 2 (task #59): module overlaps — LOW value (detector list is stale); skip/deprioritize.

## NEXT RUN

Autonomous items are real builds/probes (not one-liners) — draining them is a
large unattended spend. Per the cost model + "big autonomous run = user's call",
await a greenlight ("drain the backlog" / pick items) before a full D-run.
Recommended first (cheapest, highest-signal): #23 UniVR (calibration-gated,
$0 local) or #8 remainder (gauntlet-side).
