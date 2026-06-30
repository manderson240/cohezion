# Quarter on a String Protocol — Local-First $0 Inference (MANDATORY)

**Origin:** standing user directive (recurring). Codified 2026-06-30. Auto-loads, version-controlled.

> "Drop the quarter to register the value, pull the string so it costs nothing."

## The protocol in two sentences

Orchestrate ALL engineering work — build, verify, cross-review (Dev→QA), research, design —
on local AMD silicon (NPU → iGPU → CPU via the **:13305 OmniRouter**) at **$0**; the cloud
"quarter" is dropped **only** when a *genuine* local quality gate fails. The "string" is local
validation — we verify cloud output on local lanes before and after any spend — so the quarter
registers the value and is then reclaimed: patience + skillful orchestration ≈ unlimited
inference at $0.

## 1. Routing order (cheapest-capable first, escalate only on a gate miss)

| Tier | Engine | Default model (:13305) | Use for |
|------|--------|------------------------|---------|
| 0 | **NPU** (XDNA2) | `llama3.2-1b-FLM` | classification, routing, short categorical/answers |
| 1 | **iGPU** (RDNA3.5) | `Gemma-4-E4B-it-GGUF` / `Bonsai-8B-gguf` | structured generation, code |
| 2 | **CPU** (AVX-512) | `Gemma-4-31B-it-GGUF` / `Qwen3.6-35B-A3B-NoThinking` | multi-step reasoning, review |
| 3 | **Cloud** (metered $) | Claude / Gemini / `*:cloud` | **last resort only — see §2** |

- **Right model for the task** (the discipline that makes $0 trustworthy): `llama3.2-1b` for
  routing; an iGPU model for structured generation; the reasoning tier for genuine multi-step work.
  Do not run a 1-sentence classify on a 35B; do not run multi-step reasoning on the 1B.
- The cascade is the live wiring: `make_local_execute_fn → build_triune_omni_orchestrator`
  (NPU→iGPU→CPU, all served by :13305, all `cost_usd == 0.0`, NO cloud tier in the list).
- Per-task gate: `TieredOrchestrator.run(gate_chars=…)` from `task_classifier.classify(prompt)`
  — a correct short answer passes at the NPU instead of needlessly escalating.

## 2. The escalation gate (when the quarter is allowed to drop)

Cloud is escalated to **only on a genuine local-quality-gate failure** — never on convenience,
never on input *size* alone, never as a default.

- **Mathematical guarantee — Feynman path weight, CC2** (global `harness.md`):
  `feynman_path_weight(q, cost_usd)` with `λ=100` in
  `src/cohezion/inference/fractal_metrics.py`. Local `q=0.5 → weight 0.500` **beats** cloud
  `q=1.0` at `$0.01 → weight 0.368`. **Cloud must be ≥2.72× higher quality than local to win.**
  A local lane is preferred unless cloud is *decisively* better, not marginally.
- **What counts as a genuine gate miss** (any one, after local retries are exhausted):
  1. local output is empty / unparseable after the full NPU→iGPU→CPU cascade, OR
  2. a **Dev→QA cross-check on local lanes** (§3) fails the output against the task's
     acceptance criteria, OR
  3. a hard context-window overflow that no local model can hold (and even then, prefer a
     local long-context model before a `*:cloud` model).
- **Not a gate miss:** "the cloud model is smarter", "it's faster to just ask Claude", an
  unvalidated low-confidence guess, or a token count > 80% of a context window **with no
  quality check first**. These are quarter leaks — forbidden.

## 3. The string — Dev→QA cross-verification on local lanes (the rigor)

The output is trustworthy at $0 because it is **cross-verified locally**, not because the model
is large:

- **Dev lane** (e.g. iGPU `Gemma-4-E4B` / `Bonsai-8B`) produces the artifact.
- **QA lane** (a *second*, independent local tier — e.g. the reasoning/`review` tier) scores it
  against explicit acceptance criteria. Disagreement → escalate ONE local tier, not to cloud.
- This is the "string": cheap local validation that lets us (a) catch a genuine failure before
  paying, and (b) **verify cloud output locally after a spend** so we never pay twice for the
  same answer and we reclaim the value of the quarter.
- Two-provider pattern (already in the codebase): `build_triune_omni_orchestrator()` for
  execution, the reasoning/review tier for the QA pass.

## 4. Reclaim discipline

1. **Before** any cloud call: run the local cascade + the QA gate. Only a genuine miss proceeds.
2. **After** any cloud call: validate the cloud output on a local lane (QA gate). Cache it
   (`SemanticCache`) and record `cloud_savings_usd` so the next identical request is $0.
3. Token accounting (`TokenUsageRecord` via `make_local_execute_fn`): local = free tokens,
   cloud = metered; `session_cloud_cost_usd` is the quarter ledger — it should stay ~$0.

## Invariants this protocol depends on (do not regress)

- **N1 / Inference Ports:** `:13305` is the only port needed; per-port `:13306/7/9` are redundant.
- **CC2:** `feynman_path_weight` λ=100 — the local-beats-cloud guarantee.
- **CB5 / DegradationDetector:** routing feedback escalates *within* local tiers first.
- **Local-first default** (`local-inference-default.md`): NPU→iGPU→CPU→Cloud, cloud last resort.

## Anti-patterns (each is a quarter leak — STOP)

- Defaulting any tier to a cloud model "to be safe".
- Escalating to `*:cloud` / Claude / Gemini on input *size* or *latency* with no local quality gate.
- A "success" gate so weak (e.g. `bool(output.strip())`) it can never register a genuine
  quality failure — it can't pull the string, so it can't reclaim and can't trust.
- Paying cloud for an answer already in the `SemanticCache` or reproducible locally.
