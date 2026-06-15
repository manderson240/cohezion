---
title: Agentic Job Description — Cohezion Compound Engineering
source: arxiv:2602.19065 (Chanjin Park, SNU) — Agentic Problem Frames
version: 1.0.0
date: 2026-06-14
status: active
---

# Agentic Job Description (AJD) — Cohezion Compound Engineering

Formalizes the AVR (Act-Verify-Refine) loop boundaries per Agentic Problem Frames
theory (arXiv:2602.19065). Reliability comes from engineering structure, not model
intelligence — this document defines the operational boundaries for Cohezion agents.

## 1. Jurisdictional Boundaries

Each agent role has a clearly bounded domain. Agents MUST NOT act outside their
jurisdiction and MUST escalate rather than guess at boundary edges.

| Role | Scope | Hard Boundary |
|------|-------|--------------|
| **Maker** (execute_fn / CompoundExecutor) | Produce output for a given task | Output only; never modify task spec |
| **Checker** (MakerCheckerVerifier) | Verify output against task spec | Verdict only (pass/fail/partial); never modify output |
| **Refiner** (SkillRefiner) | Update skill definitions from execution patterns | Skills only; never modify live execution path |
| **Retrospector** (RetrospectionEngine) | Extract learnings; decide if refinement is needed | Advisory only; never block execution |
| **Degradation Monitor** (DegradationDetector) | Measure metric drift; suggest routing tier | Suggest only; never force a route |
| **Router** (CostAwareRouter / DegradationFeedback) | Select inference tier | Route selection only; never produce output |

## 2. Operational Contexts

### Act Phase (Maker)
- Input: `task_description`, `guidance` (from vault experience)
- Action: Execute `execute_fn(guidance)` → `(output, metrics)`
- Output: Raw task output
- Context: NPU/iGPU inference via Lemonade :13305
- Failure mode: Exception → error metrics, no retry in Maker

### Verify Phase (Checker)
- Input: `task_description`, `maker_output`
- Action: Call `MakerCheckerVerifier.verify_async()` with 8s timeout
- Output: `CheckerResult(verdict, confidence, reason)`
- Context: CPU-tier model (Granite-4.1-8B) via Lemonade :13305
- Failure mode: Timeout/error → `verdict='skipped'`, execution continues

### Refine Phase (SkillRefiner + RetrospectionEngine)
- Input: `ExecutionResult`, `skill_name`
- Action: Update skill definition if `retrospection.should_refine=True` AND `drr_passed=True`
- Output: Updated skill path
- Context: Vault write + pattern extraction
- Failure mode: Non-blocking, logged, never blocks result return

## 3. Epistemic Evaluation Criteria

These are the harness-enforced criteria that determine if an execution "succeeded"
at the compound engineering layer (above raw LLM output correctness):

| Criterion | Measurement | Threshold |
|-----------|------------|-----------|
| **Coherence** | `metrics["coherence"]` (precipitation + alignment) | ≥ 0.4 (HIHO band) |
| **Checker confidence** | `metrics["checker_confidence"]` | ≥ 0.7 → reliable verdict |
| **Anomaly severity** | `metrics["anomaly_severity"]` | `!= CRITICAL` for refinement |
| **Cache hit rate** | `DegradationDetector.check_degradation()` | ≥ 0.5 (CA1 invariant) |
| **Routing agreement** | `suggest_routing_tier()` vs `classify().node` | ≥ 90% (CB13 invariant) |

## 4. AVR Loop Structure (Cohezion Mapping)

```
Act:     execute_fn(guidance)              → output
Verify:  MakerCheckerVerifier.verify()    → checker_verdict
Refine:  SkillRefiner.refine()            → updated_skill_path
         (gated by RetrospectionEngine + DRR)
```

This maps directly to the CompoundExecutor.execute_task() pipeline:
- Step 3: Act (execute_fn)
- Step 3.5: Verify (MakerCheckerVerifier)
- Step 7: Refine (SkillRefiner, gated by Step 7.3 Retrospection)

## 5. Boundary Enforcement

The V-Model harness (`.claude/rules/harness.md`) structurally enforces these boundaries:

- **CB5**: ExecutorFactory auto-wires DegradationDetector + routing callback
- **CB13**: Routing accuracy invariant ensures Checker and Router agree
- **CB12**: `suggest_routing_tier()` never returns outside `{npu, igpu, cpu}`
- **SCP1-SCP5**: Session control plane structural invariants

## 6. Escalation Protocol

When an agent reaches its jurisdictional boundary:

1. **Checker returns `fail` with confidence ≥ 0.8**: Log warning, escalate to user via compound health API
2. **DegradationDetector returns CRITICAL**: Enter degradation mode, downgrade tier
3. **Coherence < 0.4 for 3 consecutive tasks**: Log to SurrealDB `traces`, emit Telegram notification
4. **Checker verdict = `fail`, coherence < 0.4**: Candidate for re-execution flag (not automatic)

## References

- arXiv:2602.19065 — Agentic Problem Frames (Chanjin Park, SNU, 2026)
- `src/cohezion/compound/maker_checker.py` — Checker implementation
- `src/cohezion/compound/executor.py` — execute_task() pipeline
- `~/.claude/rules/harness.md` — CB5, CB12, CB13 structural invariants
- `docs/SESSION_CONTROL_PLANE.md` — SCP1-5 invariants
