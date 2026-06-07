---
title: "Tutorial distillation via local inference — Marktechpost batch 1"
date: 2026-06-06
source: "github.com/Marktechpost/AI-Agents-Projects-Tutorials"
method: "scripts/research/distill_tutorials.py — lemonade :13305 Granite-4.1-8B, $0 local"
---

# Tutorial distillation (local inference, batch 1 of N)

User directive: "have local inference work through each of them." The local fleet (Granite-4.1-8B on
:13305, $0) read and distilled 6 cohezion-relevant tutorials. This is also the thread-P distillation
pipeline working (external content → local inference → digest → memory). Re-runnable for ALL tutorials
via `scripts/research/distill_tutorials.py <path...>`.

## Method-note: the SLM over-proposes; the filter is the gate
Granite proposed a "transferable lever" for ALL 6 tutorials — typical generous-SLM calibration. Applying
the research filter's two gates (fleet-runnable? / concrete instrument on a real seam?), only ONE is a
genuine new lever; the rest map to machinery cohezion already has. This is metacognitive-calibration in
action: the local model is the cheap first pass, the filter is the discriminating second pass.

| Tutorial | Local-model verdict (Granite) | Filter ruling |
|---|---|---|
| Agentic Zettelkasten Memory | embeddings + semantic linking → knowledge graph | **overlaps-existing** — semantic cache (nomic 768D) + FLUME + SurrealDB `concept`/`link` graph already do this |
| Persistent Memory (decay) | DECAYED similarity retrieval for personalization; "explicit decay logic is missing" | **GENUINE LEVER → item 109** — cohezion recall ranks by relevance but has NO recency-decay weighting |
| evermem (FAISS + SQLite) | FAISS vector + SQLite persistent memory | **overlaps-existing** — FAISS = an ANN index; cohezion has the semantic cache + the turbovec ANN eval (item 56); SurrealDB ⊇ SQLite |
| LangGraph adaptive memory + reflexion | LangGraph orchestration + reflection nodes | **overlaps-existing / drift** — CompoundExecutor (orchestration) + RetrospectionEngine (reflection) already exist; adopting LangGraph = framework drift (cf. Dify) |
| LLM Arena-as-a-Judge | head-to-head model comparison via a judge model | **validates thread-N item 99 + minor refinement** — the RHO model tournament IS arena-as-judge; refinement: item-99's `prefer` fn can be an LLM judge |
| GEPA reflective prompt evolution | automated prompt optimization via reflection feedback | **overlaps-existing** — RHO + SkillRefiner + autoresearch already evolve skills/prompts; GEPA's loop ≈ the existing refine cycle |

## Outcome
- **1 genuine lever** → backlog **item 109** (recency-decay weighting on memory recall, thread P).
- **1 refinement** → noted on item 99 (the RHO `prefer` fn can take an LLM-judge, the arena-as-judge pattern).
- **4 overlaps-existing** — confirm cohezion's memory/orchestration/eval stack already covers the standard
  agentic-memory + eval patterns these tutorials teach.

## Batches remaining (for "each of them")
Flagship repo has ~25 topic areas (A2A, MCP Codes, Agentic Workflows, Adversarial Attacks, LLM Projects,
Prompt Optimization, Computer Vision, Federated Learning, …). Batch 1 = Agentic Memory + LLM Evaluation
(the two mapping to live threads P/N). Next batches: MCP Codes, Agentic Workflows, Adversarial Attacks
(→ security_spec/I7), Prompt Optimization — runnable as a background job. Expectation set by batch 1:
mostly overlaps-existing (cohezion is mature), occasional genuine lever — the filter keeps the backlog honest.
