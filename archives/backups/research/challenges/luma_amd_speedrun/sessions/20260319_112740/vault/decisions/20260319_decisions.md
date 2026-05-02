# Session 20260319 — Strategic Decisions

**Date:** 2026-03-19  
**Agent:** Cloud Reasoning Agent (Hermes)  
**Context:** Refining V1 orchestration plan with K-Search × R-Zero × AutoResearch

---

## Decision 1: MLA is 16.7× Gap — Breakthrough Required, Not Incremental

**Problem:** Current plan focuses on incremental improvements. MLA gap is 16.7× which cannot be closed by tuning.

**Decision:** Create parallel tracks:
- **Track 1 (V=0.95):** Probe AITER for hidden ASM kernel paths
- **Track 2 (V=0.80):** Exhaustive AITER env var grid search  
- **Track 3 (V=0.30):** Custom HIP MFMA kernel with persistence

**Rationale:** K-Search teaches us to assign V-scores based on confidence. V=0.95 means "almost certain" — the leader must be using something fundamentally different (ASM kernel + persistence).

**Status:** APPROVED

---

## Decision 2: Multi-Agent Specialization (R-Zero Style)

**Problem:** V1 plan had agent stubs but no actual spawning mechanism.

**Decision:** Implement `spawn_agents.py` that:
1. Uses Ollama for code generation (qwen2.5-coder:14b)
2. Spawns parallel specialist agents per kernel
3. Updates world model with each experiment
4. Extracts skills on breakthrough

**Rationale:** R-Zero shows simple autonomous loop achieves SOTA. Multi-agent specialization accelerates exploration.

**Status:** APPROVED — Implementation created in `spawn_agents.py`

---

## Decision 3: World Model Co-Evolution (K-Search Core)

**Problem:** V1 world model exists but isn't actively guiding exploration.

**Decision:** Implement V-score update rules:
- Breakthrough (speedup > 2×): V += 0.2, extract skill
- Improvement (speedup > 1.1×): V += 0.1
- Neutral (0.95-1.1×): V unchanged  
- Regression (< 0.95×): V -= 0.05
- Crash/error: V -= 0.1
- Stagnation (K=7 fails): Mark stale, explore alternatives

**Rationale:** K-Search's co-evolution principle — world model must update after each experiment to guide future exploration.

**Status:** APPROVED — Implementation in `run_orchestration.py`

---

## Decision 4: Experiential Recursive Learning

**Problem:** No skill extraction from successful experiments.

**Decision:** After each breakthrough:
1. Extract pattern to `vault/skills/` in R-Zero format:
   ```markdown
   ## Skill: MLA-MFMA-Persistent-001
   [[observation]] — Context before
   [[action]] — What changed
   [[reward]] — Performance delta
   ```
2. Check cross-kernel transfer opportunities
3. Update `vault/patterns/` with new findings

**Rationale:** R-Zero's recursive skill acquisition enables learning from experience. Skills compound over iterations.

**Status:** APPROVED — Skill extraction in `spawn_agents.py`

---

## Decision 5: MoE and GEMM Maintenance Mode

**Problem:** MoE gap is 1.03× (almost there), GEMM gap is 2.3×.

**Decision:** 
- MoE: Continue with current adaptive KSPLIT approach (V=0.90)
- GEMM: Focus on inline quantization to eliminate 10-13µs overhead (V=0.70)
- Both: Secondary priority to MLA breakthrough

**Rationale:** Per K-Search priority scoring: impact × confidence. MLA has highest impact (16.7× gap) and decent confidence (V=0.80-0.95).

**Status:** APPROVED

---

## Decision 6: Ollama Local Model Integration

**Finding:** Ollama is available at localhost:11434 with:
- `qwen2.5-coder:14b` — Code generation
- `deepseek-r1:7b` — Strategic reasoning  
- `phi3:mini` — Fast updates
- `cohezion_v2:latest` — Domain-specific model

**Decision:** Use local Ollama for:
1. Code generation (replaces manual writing)
2. Strategic reasoning (replaces Claude Code for routine decisions)
3. World model updates (phi3:mini for speed)

**Rationale:** R-Zero emphasizes iteration speed. Local models enable rapid experimentation without API costs or rate limits.

**Status:** APPROVED

---

## Decision 7: Exit Conditions

**Decision:** Stop autonomous research when:
1. **MLA < 10µs** — Breakthrough achieved (7× improvement)
2. **All three kernels in top-10** — Qualifier goal met
3. **100 iterations** — Resource limit
4. **Human explicit stop** — Mike intervention

**Rationale:** Clear exit prevents infinite loops. Top-10 is qualifier requirement; 10µs MLA is breakthrough threshold.

**Status:** APPROVED

---

## Summary of Changes from V1

| Aspect | V1 Plan | V2 Plan (This Session) |
|--------|---------|------------------------|
| MLA Strategy | Incremental tuning | Parallel breakthrough tracks |
| Agents | Stubs only | Full spawning implementation |
| World Model | Passive | Active V-score updates |
| Skill Extraction | None | R-Zero format extraction |
| Code Gen | Manual | Ollama-powered |
| MoE/GEMM | Equal priority | Maintenance mode |

---

## Next Steps

1. Run `python spawn_agents.py --kernel mla --all` to generate initial variants
2. Submit to popcorn-cli for benchmarking
3. Update world model with results
4. Extract skills on breakthrough
5. Repeat iteration loop

---

**Approved by:** Cloud Reasoning Agent  
**Review date:** After first iteration cycle
