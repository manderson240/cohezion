---
title: "Strategic Plan: Maximize Strengths, Minimize Weaknesses"
date: "2026-04-11"
session: "96b (post-retrospective)"
status: "ACTIVE"
---

# Strategic Plan: Maximize Strengths, Minimize Weaknesses

## Strengths to AMPLIFY

### S1: Physics Grounding (UNIQUE DIFFERENTIATOR)
**What:** 12D Riemannian manifold, SU(2) spinors, Fisher metric Rosetta Stone, Mereon 600-cell, Euler-Lagrange dynamics, SIGReg-HIHO equivalence with LeWM.
**Why it matters:** No published agentic system has physics-grounded RL environments with mathematically verifiable invariants. This is what the Universes team builds.
**Amplify by:**
- [ ] Complete physics proof obligation suite (add gauge invariance ∇·B=0, Liouville's theorem)
- [ ] Publish the SIGReg-HIHO equivalence proof as a technical note
- [ ] Wire verifiable reward signals (r_hiho, r_conservation, r_unitarity) into ManifoldEnv
- [ ] Implement LeWM dual-loss training for JEPA (Phase 3 of architecture plan)

### S2: Verified Architecture (SLR-CONFIRMED NOVEL)
**What:** V-Model gates + bi-temporal KG + physics RL + hash-chain audit + formal invariants. 0 published systems combine 3+ components.
**Why it matters:** Defensibility tier A-S, not just "tests pass."
**Amplify by:**
- [ ] Implement hash-chain in JourneyTracker (Task 8.1 — addresses OLIF vulnerability)
- [ ] Complete DRR generator (Task 4.3)
- [ ] Wire proof obligations into compound executor pipeline (Task 4.4)
- [ ] Write the SLR paper using the protocol at docs/papers/systematic-review-protocol.md

### S3: Compute Fabric (QUARTER-ON-A-STRING)
**What:** 105+ Lemonade models (local, $0) + Ollama Pro cloud ($20/mo) + Claude Max 20x + Gemini Pro orchestration.
**Why it matters:** Zero marginal cost for experimentation. Can run 122B models locally.
**Amplify by:**
- [ ] Complete tier-based routing in CostAwareRouter (remaining 18 refs → switch to Lemonade targets)
- [ ] Implement hotswapping in ModelPoolManager (raise max_loaded_models from 1 to 2-3)
- [ ] Daily model scout → auto-integrate new SOTA models into Lemonade
- [ ] Benchmark Lemonade vs Ollama latency/quality for each tier

### S4: Compound Learning Loop (CLOSEST TO GENUINE LEARNING)
**What:** CompoundExecutor + SkillRefiner + RetrospectionEngine + JourneyTracker + DegradationDetector.
**Why it matters:** Most agent systems do memory (stored text). Cohezion does learning (behavioral change).
**Amplify by:**
- [ ] Validate skill refinement with before/after metrics (Weakness W1 fix)
- [ ] Cross-check retrospection against journey traces (Weakness W2 fix)
- [ ] Add tape logger for deterministic replay (Weakness W3 fix)

---

## Weaknesses to ELIMINATE

### W1: Skill Refinement Unvalidated (HIGH PRIORITY)
**Risk:** SkillRefiner may be making skills worse without detection.
**Fix:** Add `SkillRefinementValidator` that records success_rate, avg_latency, coherence for N executions before mutation, then compares same metrics after. Store in SurrealDB `model_artifacts` with lineage. Block mutations that degrade metrics >5%.
**Effort:** 1 session | **Impact:** Closes the compound loop's biggest trust gap

### W2: Retrospection Unverified (HIGH PRIORITY)
**Risk:** Retrospection summaries may not match actual execution traces (OLIF vulnerability).
**Fix:** `RetrospectionValidator` cross-references summary claims against journey_transitions in SurrealDB. For each claim ("coherence improved by X"), verify against actual trajectory data. Flag discrepancies.
**Effort:** 1 session | **Impact:** Makes acceptance testing trustworthy

### W3: No Deterministic Replay (MEDIUM PRIORITY)
**Risk:** Can't reproduce compound executions. Debug by guess, not replay.
**Fix:** `TapeLogger` records every LLM prompt/response/model/temperature to JSONL. `tape_replay=True` mode reads from tape instead of calling LLM. Enables exact reproduction of any session.
**Effort:** 1 session | **Impact:** Enables regression testing of compound loop behavior

### W4: OLIF Vulnerability (HIGH PRIORITY)
**Risk:** Agents can fabricate audit evidence (documented across 135+ interactions in research).
**Fix:** Hash-chain audit trail in JourneyTracker. Each transition hashes to previous. External verification possible. Schema already exists (hash_chain table created this session).
**Effort:** 0.5 session (schema done, implementation needed) | **Impact:** Moves from Tier D (self-reported) to Tier A (cryptographically auditable)

### W5: Adapter Stubs Incomplete (MEDIUM PRIORITY)
**Risk:** dynamic_system_integration.py has 10 `# IMPLEMENT:` stubs. Adapters don't actually wire the proactive engine to existing infrastructure.
**Fix:** Complete all 10 stubs + add LemonadeAdapter for hotswapping.
**Effort:** 1 session | **Impact:** Full proactive/reactive engine integration

### W6: Thread Safety in Profile Cache (LOW PRIORITY)
**Risk:** Race condition in async context — two coroutines could see partially populated MODEL_COSTS.
**Fix:** Add `threading.Lock` around `_ensure_profiles_loaded()`.
**Effort:** 5 minutes | **Impact:** Eliminates rare async race

### W7: KEY_LEARNINGS Duplicate Numbers (LOW PRIORITY)
**Risk:** L304-L307 have different content from parallel sessions.
**Fix:** Reconcile — renumber Session 97's L304-L307 to L310-L313. Session 96b's L304-L309 stay.
**Effort:** 10 minutes | **Impact:** Clean knowledge graph

---

## Token-Efficient Model Routing Policy

**For Claude Code agent teams (orchestration layer):**

| Task Complexity | Model | Cost | Examples |
|----------------|-------|------|---------|
| Mechanical/simple | **Haiku 4.5** | $0.25/M in | File moves, dedup, grep, formatting, simple edits |
| Implementation | **Sonnet 4.6** | $3/M in | Code changes, test writing, schema design |
| Architecture | **Opus 4.6** | $15/M in | Design decisions, plan reviews, adversarial review |

**For compound loop inference (inference layer):**

| Tier | Provider | Cost | Use Case |
|------|----------|------|----------|
| Hot | **Lemonade Hybrid** (Phi-4-mini, Qwen3-8B) | $0 | Skill selection, alignment analysis, fast routing |
| Warm | **Lemonade GPU** (Qwen3-14B, Gemma-4-31B) | $0 | Complex reasoning, vision tasks |
| Cold | **Lemonade GPU** (Qwen3.5-122B, gpt-oss-120b) | $0 | Frontier-quality local inference |
| Cloud | **Ollama Pro :cloud** (deepseek-v3.2, cogito-2.1) | $20/mo | Models exceeding 96GB UMA |

**For background/research tasks:**

| Task | Route To | Why |
|------|----------|-----|
| /anthropic-scan | Ollama :cloud (qwen3.5:cloud) | Don't burn Claude tokens on web fetch summarization |
| Daily model scout | Lemonade CPU (DeepSeek-R1-8B-CPU) | Background task, no GPU contention |
| Vault-keeper cycle | Lemonade Hybrid (Qwen3-4B-Hybrid) | Neuron extraction from markdown |
| Embedding generation | Lemonade (nomic-embed-text-v2) | Local GraphRAG, zero cost |

**Dynamic 3-Slot Lemonade Architecture:**

Each backend runs one model concurrently — no contention because different hardware:

| Slot | Backend | Hardware | Persistent Default | Hotswap Candidates | Task Affinity |
|------|---------|----------|-------------------|-------------------|---------------|
| NPU | RyzenAI 1.7 | XDNA2 (16GB) | Phi-4-mini-reasoning | Qwen3-8B, CodeLlama-7b, Qwen2.5-Coder-7B | Fast reasoning, coding |
| GPU | ROCm llamacpp | RDNA 3.5 (UMA) | Qwen3-14B-GGUF | Gemma-4-31B, Qwen3.5-122B, gpt-oss-120b | Quality reasoning, vision, frontier |
| CPU | ONNX int4 | Ryzen 32T | DeepSeek-R1-8B-CPU | Phi-3-Mini-CPU, Qwen-7B-CPU | Background tasks, no GPU contention |

**Hotswap triggers (CostAwareRouter decides dynamically):**
- Coding task → NPU slot hotswaps to CodeLlama-7b or Qwen2.5-Coder-7B
- Vision task → GPU slot hotswaps to Gemma-4-31B-it (has mmproj)
- Frontier reasoning → GPU slot hotswaps to Qwen3.5-122B (68GB, uses most UMA)
- Background embedding → CPU slot, no swap needed (runs alongside NPU+GPU)

**Implementation:**
- `vendor/lemonade/config.json`: Change `max_loaded_models: 1` → `3`
- `LemonadeManager.hotswap(slot, new_model)`: Unload current model from slot, load new one
- `CostAwareRouter._select_backend(task_type)`: Map task → backend slot → model
- Pi agent coordination: When Pi needs Lemonade, it gets NPU slot priority; Cohezion uses GPU+CPU

**Guardrails:**
- Max 2 Ollama :cloud concurrent slots for Cohezion (1 reserved for Pi)
- Lemonade: 3 concurrent slots (NPU + GPU + CPU), dynamic hotswap per task
- Pi agent gets NPU priority; coordinate via lockfile or health check
- Never use Opus for tasks that Haiku can handle — 60x cost difference
- Tape-log all LLM calls regardless of provider (for deterministic replay)
- GPU slot: monitor UMA usage — if Qwen3.5-122B (68GB) is loaded, no room for second GPU model

## Sprint Priority Matrix

| Sprint | Focus | Addresses | Sessions |
|--------|-------|-----------|----------|
| **Sprint 1** | W1 + W2: Validate compound loop | Skill refinement + retrospection validation | 1-2 |
| **Sprint 2** | W4 + S2: Hash-chain audit trail | OLIF fix + DRR generator | 1 |
| **Sprint 3** | S1 + S4: Physics + tape logger | Conservation suite + deterministic replay | 1-2 |
| **Sprint 4** | S3 + W5: Compute fabric + adapters | Lemonade routing + adapter stubs | 1-2 |
| **Sprint 5** | S2: SLR paper | Write and submit systematic review | 3-5 |
| **Sprint 6** | S1: LeWM JEPA + verifiable rewards | Dual-loss training + ManifoldEnv rewards | 2-3 |
| **Sprint 7** | GraphRAG + DPAM | Unified queries + agent-governed data products | 2-3 |

**Total: ~15-20 sessions to complete all phases.**

## Token-Efficient Compound Systems Engineering Solutions

Every gap maps to a V-Model gate. Every fix uses the cheapest model that can do the job. Every deliverable is testable.

### Gap → Solution → Model → Gate Matrix

| Gap | SE Solution | Agent Model | V-Model Gate | Test |
|-----|------------|-------------|-------------|------|
| W1: Skill refinement unvalidated | SkillRefinementValidator with before/after metrics | Sonnet (design) + Haiku (metrics collection) | DRR-1 | `test_skill_improvement_measured()` |
| W2: Retrospection unverified | RetrospectionValidator cross-checks against SurrealDB traces | Sonnet (logic) + Haiku (query execution) | DRR-0 | `test_retrospection_matches_traces()` |
| W3: No deterministic replay | TapeLogger JSONL + replay mode | Sonnet (implementation) | DRR-3 | `test_tape_replay_deterministic()` |
| W4: OLIF vulnerability | Hash-chain in JourneyTracker (DONE) | — | DRR-0 | `verify_chain()` returns True |
| W5: Adapter stubs | Complete 10 stubs + LemonadeAdapter | Haiku (mechanical) + Sonnet (LemonadeAdapter) | DRR-2 | Existing adapter tests |
| Physics conservation gaps | Add gauge invariance + Liouville tests | Haiku (test writing) | DRR-3 | 5 new proof obligations |
| Dynamic model hotswap | LemonadeManager.hotswap(slot, model) | Sonnet | DRR-2 | `test_hotswap_npu_gpu_cpu()` |
| SLR paper | Execute search queries + write synthesis | Ollama :cloud (research summarization) | — | Peer review |
| Vault repopulation | Run vault-keeper-cycle on fresh SurrealKV | Lemonade CPU (background) | — | Graph HIHO > 0.35 |

### Compound Execution Pattern (for all sprints)

```
1. PLAN (Opus/Sonnet): Design solution, write test spec
2. HASH-LOCK: SHA-256 hash test files → store in vmodel_gate
3. IMPLEMENT (Sonnet/Haiku): Write code, tests must stay immutable
4. VERIFY (Haiku): Run tests, check proof obligations
5. DRR (Sonnet): Generate Design Review Report
6. PERSIST (Lemonade CPU): Log to SurrealDB, update vault
7. COMPOUND: Extract pattern → refine skill → update plan
```

This pattern uses 4 models across 7 steps — Opus only for design, Sonnet for implementation, Haiku for verification/mechanical work, Lemonade for persistence. Total cost per sprint: ~$0.50-2.00 in Claude tokens + $0 in inference.

### 3-Slot Dynamic Lemonade Allocation Per Sprint

| Sprint Phase | NPU Slot | GPU Slot | CPU Slot |
|-------------|----------|----------|----------|
| Planning | Phi-4-reasoning (fast drafts) | idle | DeepSeek-R1-CPU (background research) |
| Implementation | CodeLlama-7b (code assist) | Qwen3-14B (quality review) | idle |
| Testing | idle | idle | DeepSeek-R1-CPU (test generation) |
| Persistence | idle | nomic-embed-v2 (embeddings) | Phi-3-Mini-CPU (summarization) |

---

## Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|---------------|
| Physics proof obligations | 10 tests | 20+ tests | `pytest tests/physics/test_conservation_laws.py` |
| Skill refinement validation rate | 0% | 100% | Before/after metrics for every mutation |
| Retrospection accuracy | Unknown | >95% | Cross-check against journey traces |
| Audit trail coverage | 0% hash-chained | 100% of journey transitions | hash_chain table row count |
| Deterministic replay capability | None | Full tape logging | Replay success rate on historical sessions |
| Model routing via config | 63% (30/48 refs) | 100% | `grep -c` hardcoded model names |
| SLR paper status | Protocol + preliminary results | Submitted | Paper at target venue |
| DRR gates in /spec | 0 implemented | 4 (DRR-0 through DRR-3) | Gate records in vmodel_gate table |

---

## The Universes Pitch (Refined)

Cohezion is a **research-grade agentic universe simulation platform** that uniquely integrates:

1. **Physics-grounded RL environments** — 12D Riemannian manifold with SU(2) spinors, Euler-Lagrange dynamics, and the SIGReg-HIHO equivalence (proven correspondence between LeWM's Gaussian regularizer and HIHO's coherence stability)

2. **Bi-temporal knowledge graph persistence** — SurrealKV with VERSION clause for system-time travel and valid_from/valid_to for domain-time, enabling "what did we know at time T about state at time T'?"

3. **V-Model verification lifecycle** — Hash-locked Design Review Reports at 4 lifecycle gates, with deterministic proof obligations (energy conservation, unitarity, gauge invariance, HIHO stability) constraining nondeterministic agent work

4. **Cryptographic audit trails** — Hash-chain tamper-evident journey tracking addressing the OLIF vulnerability (agents fabricating audit evidence), moving from self-reported (Tier D) to cryptographically auditable (Tier A)

5. **Compound learning loop** — Not just agent memory (stored text) but genuine behavioral change through validated skill refinement, verified retrospection, and deterministic replay capability

Our systematic literature review of N studies across 7 databases (2023-2026) found **zero published systems combining even 3 of these 5 components**. Cohezion integrates all five into a single compound engineering framework with 3,500+ tests, 10 physics proof obligations, and 4 SurrealDB traceability tables.

**This is not a chatbot scaffold. It's a training environment where every agent action is traceable, every physics step is verifiable, every knowledge update is auditable, and every compound loop iteration is defensible.**
