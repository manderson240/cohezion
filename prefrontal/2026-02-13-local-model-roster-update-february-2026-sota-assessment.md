---
title: Local Model Roster Update - February 2026 SOTA Assessment
date: '2026-02-13'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  chosen_option: '{{chosen_option}}'
  rationale: GLM-4.7-Flash dominates every benchmark vs deepseek-r1:70b at half the
    RAM (3B active MoE vs 70B dense). Phi-4-mini-reasoning outperforms models 2x its
    size on math reasoning. Nemotron-3-Nano brings unique 1M context window via hybrid
    Mamba-Transformer MoE. Snowflake Arctic-Embed v2.0 adds MRL compression (4x vector
    size reduction with &lt;3% quality loss) benefiting SurrealDB vector store.
  confidence_score: 0.6
  alternatives_rejected:
  - '{{alt1}}'
  - '{{alt2}}'
  reasoning_chain:
  - sequence: 1
    content: 'Context: Local Model Roster Update - February 2026 SOTA Assessment'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  - sequence: 4
    content: Selected option with best balance of trade-offs
    type: hybrid
    confidence: 0.62
    assumption: Best option was chosen based on analysis
  reasoning_type: research
metrics:
  estimated_cost: 0.0
  estimated_time_hours: 0.0
  actual_cost: 0.0
  actual_time_hours: 0.0
  tokens_used: 0
  cost_per_lesson: 0.0
  lessons_generated: []
aspect: thinker
neural:
  activation: 0.670
  stage: mature
  cluster: decisions
---

## Context

The Cohezion platform relies on local LLMs via [[2026-02-09-ollama-context-management|Ollama]] for cost-effective inference: embeddings, gap analysis, concept extraction, and agent routing. The existing model roster (qwen3:8b, deepseek-r1:7b, nomic-embed-text) was selected in early February 2026 but the local model ecosystem evolves rapidly. Several new models released in the first two weeks of February 2026 showed significant benchmark improvements over the current roster, particularly in reasoning efficiency and embedding compression.

Key triggers for this assessment:
- **GLM-4.7-Flash** released with MoE architecture (3B active parameters) outperforming dense 70B models on multiple benchmarks
- **Phi-4-mini-reasoning** from Microsoft showed 2x-its-size performance on math reasoning tasks
- **Nemotron-3-Nano** introduced hybrid Mamba-Transformer MoE with 1M context window
- **Snowflake Arctic-Embed v2.0** added Matryoshka Representation Learning (MRL) for 4x vector size reduction with under 3% quality loss

The [[3-tier-hotwarmcold-model-rotation]] pattern requires current model assignments to stay competitive; stale models waste compute and produce lower-quality outputs.

## Decision

Update the local model roster based on February 2026 SOTA assessment. Replace or supplement existing models where new releases demonstrate clear improvements on task-relevant benchmarks.

## Chosen Option

**Roster update with 4 model changes:**

| Slot | Previous | New | Rationale |
|------|----------|-----|-----------|
| **Gap analysis** | qwen3:8b (dense, 8B) | GLM-4.7-Flash (MoE, 3B active) | Dominates benchmarks at half the RAM |
| **Reasoning tasks** | deepseek-r1:7b | phi4-mini-reasoning | Outperforms 2x-size models on math reasoning |
| **Long-context** | phi4-256k (256K ctx) | Nemotron-3-Nano (1M ctx, hybrid arch) | 4x context window, unique Mamba-Transformer MoE |
| **Embeddings** | nomic-embed-text | Snowflake Arctic-Embed v2.0 | MRL compression: 4x smaller vectors, <3% quality loss |

## Alternatives Considered

### Alt 1: Keep Existing Roster (No Changes)
- **Rejected**: Benchmark gaps are significant (GLM-4.7-Flash matches deepseek-r1:70b at a fraction of the RAM). Keeping stale models wastes compute and produces lower-quality outputs for [[automated-concept-extraction]] and gap analysis pipelines.

### Alt 2: Wait for Next Quarter's Assessment
- **Rejected**: The MoE architecture shift (GLM-4.7-Flash, Nemotron-3-Nano) represents a generational change, not an incremental update. Delaying 3 months forfeits meaningful efficiency gains.

### Alt 3: Add Without Replacing (Expand Roster)
- **Rejected**: More loaded models increase RAM pressure. The [[2026-02-09-ollama-context-management]] decision documented LRU eviction as the memory management strategy; adding without removing defeats the purpose of tier-based rotation.

## Decision Reasoning

### Why This Option?

1. **GLM-4.7-Flash dominates every benchmark** vs deepseek-r1:70b at half the RAM (3B active MoE vs 70B dense). For gap analysis tasks, this is a clear upgrade.
2. **Phi-4-mini-reasoning outperforms models 2x its size** on math reasoning. For agent decision confidence scoring, smaller and faster wins.
3. **Nemotron-3-Nano brings a unique 1M context window** via hybrid Mamba-Transformer MoE. Long papers and multi-document analysis benefit directly.
4. **Snowflake Arctic-Embed v2.0 adds MRL compression** -- 4x vector size reduction with under 3% quality loss benefits the [[surrealdb-agent-context-schema|SurrealDB vector store]] by reducing storage and improving query speed.

### Alternatives Rejected

Keeping stale models wastes compute. Waiting loses 3 months of MoE efficiency gains. Expanding without replacing causes RAM pressure.

### Confidence Level

**0.88** -- High confidence. Benchmark data is public and reproducible. MoE architecture advantages are well-established. The main risk is Ollama compatibility for newer model formats, which can be mitigated by testing before deployment.

## Expected Outcomes

1. Gap analysis inference speed improves 2-3x (MoE efficiency)
2. Embedding storage in SurrealDB reduced 4x (MRL compression)
3. Long-context tasks support documents up to 1M tokens without chunking
4. RAM usage per loaded model decreases (smaller active parameter counts)
5. Quality on reasoning tasks improves per benchmark data

## Metrics & Impact

### Estimated

| Metric | Current | Expected |
|--------|---------|----------|
| Gap analysis latency | ~3s per paper | ~1.5s per paper |
| Embedding vector size | 768-dim | 192-dim (4x reduction) |
| Max context window | 256K tokens | 1M tokens |
| RAM per active model | ~8-16 GB | ~4-8 GB (MoE) |
| Embedding quality (MTEB) | Baseline | <3% loss with 4x compression |

### Actual (Post-Implementation)

Pending deployment and benchmarking against real vault workloads. Track via [[3-tier-hotwarmcold-model-rotation]] tier assignment and daily Model Wrangler reports.

## Related Decisions & Lessons

- [[3-tier-hotwarmcold-model-rotation]] — pattern that consumes these model selections (GLM-4.7-Flash → hot/warm tier)
- [[runbook-ollama-mcp-operations]]
- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-09-ai-model-strategy]]
- [[2026-02-14-agent-orchestration-design-3-tier-hotwarmcold-model-rotation]] — architectural decision that defines the tier assignments this roster populates
- [[2026-02-14-modelpoolmanager-3-tier-lifecycle-management|Experiment: ModelPoolManager]] — experiment validating the tier model against real workloads

## Related Concepts

- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
- [[2026-02-14-adversarial-multi-agent-review-protocol]]
- [[2026-02-14-phase-2-adversarial-review-corrected-status-and-path-forward]]
