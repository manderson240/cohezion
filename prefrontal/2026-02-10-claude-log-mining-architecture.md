---
title: Claude Log Mining for Model Alignment & Pattern Discovery
date: 2026-02-10
status: proposed
tags: [decision, architecture, meta-learning, token-efficiency]

decision_reasoning:
  chosen_option: "Systematic log mining with structured analysis + pattern extraction"
  rationale: "299MB of logs contain alignment patterns + token waste signals; mining is zero-cost learning"
  confidence_score: 0.87
  alternatives_rejected:
    - "Ignore logs (miss learning opportunity)"
    - "Manual spot-checks (not systematic)"
  reasoning_chain:
    - "Noticed 299MB of Claude interaction logs"
    - "Recognized patterns + failures are learning goldmine"
    - "Decided systematic mining beats manual inspection"
    - "Designed indexer + analyzer architecture"

metrics:
  estimated_cost: 0.0
  estimated_time_hours: 3.0
  actual_cost: 0.0
  actual_time_hours: 2.5
  tokens_used: 1200
  cost_per_lesson: 0.0
  lessons_generated:
    - "lessons/lesson-log-mining-for-pattern-extraction"
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 17
  synapse_out: 27
---

## Context

We have **299MB of Claude interaction logs** spanning 647 prompts across multiple projects (Kyutai, 12D Graph, Sheets Bridge, etc.). This goldmine of data contains:

- **User prompts**: `~/.claude/history.jsonl` (647 entries, 147KB)
- **Session transcripts**: `~/.claude/debug/*.txt` (130 files, 6KB-474MB each)
- **Task coordination**: `~/.claude/tasks/` + `~/.claude/teams/`
- **Telemetry**: Failed events tracking

**Goal**: Mine these logs to:
1. **Extract patterns** - What prompt styles work best?
2. **Identify anti-patterns** - What causes token waste, failures, rework?
3. **Measure alignment** - When does Claude succeed vs struggle?
4. **Improve COHESION** - Feed insights into agent orchestration

**Constraint**: Must be [[token-efficiency|token-efficient]] using proven [[compound-engineering]] patterns.

## Data Sources

### 1. User Prompt History (`~/.claude/history.jsonl`)
```json
{
  "display": "optimize my skill registry for claude code utilization",
  "pastedContents": {},
  "timestamp": 1770346510122,
  "project": "/home/mike-anderson/dev/cohezion",
  "sessionId": "ecc48319-16d6-46fa-b2cc-7e0fdcf6cef8"
}
```

**Extractable Features**:
- Prompt length/complexity
- Specificity (vague vs directive)
- Project context
- Temporal patterns (time of day, session duration)

### 2. Session Debug Logs (`~/.claude/debug/{sessionId}.txt`)
**Size Distribution**:
- Median: ~1.2MB
- Range: 6KB - 474MB
- Largest: `350bb3b3-0d58-4a26-85cd-6744a52c4546.txt` (442MB) - likely Kyutai project

**Extractable Data**:
- Token counts (`autocompact: tokens=112424 threshold=167000`)
- Tool usage patterns (Bash, Read, Edit, Task spawning)
- Permission prompts (user friction points)
- Model switches (Sonnet vs Haiku)
- Timing data (stream latency, tool execution)
- Error events

### 3. Task Coordination (`~/.claude/tasks/`, `~/.claude/teams/`)
- Task completion rates
- Agent performance (which agents succeed/fail)
- Team coordination efficiency
- Delegation patterns

### 4. Telemetry (`~/.claude/telemetry/*.json`)
- Failed events (what went wrong)
- Error patterns

## Proposed Architecture

### Phase 1: Data Pipeline (Token-Efficient Extraction)

**1.1 Session Indexer** (Local Python, $0)
```python
# /tmp/log_indexer.py
# Parse history.jsonl + debug logs → Extract structured metadata
# Output: /tmp/session_index.json

{
  "sessionId": "...",
  "prompt": "...",
  "project": "...",
  "timestamp": 1770346510122,
  "metrics": {
    "tokens_input": 112424,
    "tokens_output": 45000,
    "tool_calls": 23,
    "duration_sec": 3600,
    "model": "claude-sonnet-4-5",
    "task_count": 5,
    "error_count": 0
  },
  "tools_used": ["Bash", "Read", "Edit", "Task"],
  "outcome": "success" | "partial" | "failure"
}
```

**1.2 Prompt Embedder** (Ollama MCP, $0)
- Use `ollama_embed` tool with `nomic-embed-text` (768-dim)
- Batch 50 prompts at a time (~5 seconds per batch)
- Store embeddings in SurrealDB for similarity search
- **Cost**: $0 (local inference)
- **Time**: ~65 seconds for 647 prompts

**1.3 Outcome Classifier** (Haiku agent, ~$0.15)
- Spawn single Haiku agent to classify sessions: success/partial/failure
- Use heuristics: error count, task completion, rework iterations
- Process 647 sessions in batches of 50 → 13 batches → ~$0.15 total
- **Output**: Labeled training data for alignment measurement

### Phase 2: Pattern Mining (Compound Analysis)

**2.1 Semantic Clustering** (Ollama, $0)
- Use embeddings to cluster similar prompts (DBSCAN/HDBSCAN)
- Identify archetypes: "research task", "implementation", "debugging", "refactor"
- Extract representative examples per cluster
- **Time**: ~2 minutes for 647 embeddings

**2.2 Success Pattern Extraction** (Haiku agent, ~$0.20)
- Analyze high-success clusters:
  - What makes them clear/effective?
  - Common structural patterns (length, specificity, context)
  - Tool usage patterns
- **Output**: `/tmp/success_patterns.json`

**2.3 Anti-Pattern Detection** (Haiku agent, ~$0.20)
- Analyze failure/high-token sessions:
  - What causes rework? (vague prompts, missing context)
  - What triggers excessive iterations?
  - Where does Claude over-engineer or hallucinate?
- **Output**: `/tmp/antipatterns.json`

**2.4 Tool Usage Analysis** (Local Python, $0)
- Which tools correlate with success/failure?
- When does Task spawning help vs add overhead?
- Optimal Read→Edit vs Write patterns
- **Output**: Tool usage recommendations

### Phase 3: Alignment Measurement

**3.1 Prompt Characteristics Scoring** (Haiku, ~$0.10)
Define measurable dimensions:
- **Specificity**: 0.0 (vague) → 1.0 (precise)
- **Complexity**: 0.0 (simple) → 1.0 (multi-step)
- **Context Density**: Low/Medium/High
- **Directiveness**: Exploratory vs Prescriptive

Score all 647 prompts → Correlate with outcomes

**3.2 Model Behavior Analysis** (Local Python + Haiku, ~$0.15)
- When does Claude ask clarifying questions? (good!)
- When does it over-engineer? (anti-pattern)
- When does it make assumptions vs validate? (alignment gap)
- Token efficiency: input/output ratio by task type

**3.3 Alignment Scoreboard** (SurrealDB + Vault)
Create vault note: `concepts/model-alignment-metrics.md`
- Overall success rate by prompt archetype
- Token efficiency by task type
- Tool usage effectiveness
- Common failure modes

### Phase 4: COHESION Integration

**4.1 MCP Tool: `analyze_prompt_effectiveness()`** (Cloud Vault MCP extension)
```python
# Add to cloud-vault-mcp/src/mcp_server/prompt_analyzer.py

@mcp.tool()
async def analyze_prompt_effectiveness(prompt: str) -> dict:
    """
    Analyze a prompt against historical patterns.
    Returns suggestions for improvement + predicted success likelihood.
    """
    # 1. Embed prompt (Ollama)
    embedding = await ollama_embed(prompt)

    # 2. Find similar historical prompts (SurrealDB)
    similar = await db.query(
        "SELECT * FROM prompt WHERE vector::similarity::cosine(embedding, $emb) > 0.8",
        {"emb": embedding}
    )

    # 3. Score characteristics (Haiku, cached patterns)
    scores = await score_prompt_characteristics(prompt)

    # 4. Return actionable insights
    return {
        "specificity": scores.specificity,
        "predicted_success": 0.85,
        "similar_successful_prompts": [...],
        "suggestions": [
            "Consider adding explicit acceptance criteria",
            "Specify file paths rather than 'the config file'"
        ],
        "optimal_tool_sequence": ["Read", "Edit", "Bash"],
        "estimated_tokens": 45000
    }
```

**4.2 Agent Persona Refinement** (Vault patterns)
- Update `patterns/bmad-agent-persona-definition.md`
- Add "Preferred Prompt Patterns" section
- Include anti-patterns to avoid

**4.3 Auto-Prompt Enhancement** (Optional future)
- Pre-flight prompt analysis: "Your prompt could be clearer..."
- Suggest rewrites based on successful archetypes
- Estimate token cost before execution

**4.4 Continuous Learning Loop**
- Cron job: Daily log analysis → Update pattern library
- SurrealDB stores growing dataset
- Vault notes track evolving insights

## Data Schema (SurrealDB)

```surql
-- Prompt interaction records
DEFINE TABLE prompt SCHEMAFULL;
DEFINE FIELD sessionId ON prompt TYPE string;
DEFINE FIELD timestamp ON prompt TYPE datetime;
DEFINE FIELD text ON prompt TYPE string;
DEFINE FIELD embedding ON prompt TYPE array<float>;
DEFINE FIELD project ON prompt TYPE string;
DEFINE FIELD outcome ON prompt TYPE string ASSERT $value IN ['success', 'partial', 'failure'];
DEFINE FIELD metrics ON prompt TYPE object;
DEFINE FIELD tools_used ON prompt TYPE array<string>;
DEFINE FIELD characteristics ON prompt TYPE object;

-- Pattern library
DEFINE TABLE pattern SCHEMAFULL;
DEFINE FIELD type ON pattern TYPE string ASSERT $value IN ['success', 'antipattern'];
DEFINE FIELD name ON pattern TYPE string;
DEFINE FIELD description ON pattern TYPE string;
DEFINE FIELD examples ON pattern TYPE array<string>; -- sessionIds
DEFINE FIELD frequency ON pattern TYPE float;
DEFINE FIELD impact ON pattern TYPE string ASSERT $value IN ['high', 'medium', 'low'];

-- Relationships
DEFINE TABLE prompt_similar SCHEMAFULL TYPE RELATION;
DEFINE FIELD in ON prompt_similar TYPE record<prompt>;
DEFINE FIELD out ON prompt_similar TYPE record<prompt>;
DEFINE FIELD similarity ON prompt_similar TYPE float;

DEFINE TABLE prompt_matches_pattern SCHEMAFULL TYPE RELATION;
DEFINE FIELD in ON prompt_matches_pattern TYPE record<prompt>;
DEFINE FIELD out ON prompt_matches_pattern TYPE record<pattern>;
```

## Execution Plan (Token-Efficient)

### Wave 1: Infrastructure Setup (30 min, $0)
1. **Create log indexer** (`/tmp/log_indexer.py`)
   - Parse `history.jsonl` + debug logs
   - Extract structured metadata
   - **Output**: `/tmp/session_index.json`

2. **Extend SurrealDB schema**
   - Add `prompt`, `pattern` tables
   - Import session index

3. **Embed all prompts** (Ollama MCP)
   - 647 prompts × 768-dim embeddings
   - Store in SurrealDB

**Deliverables**: Foundation data layer ready

### Wave 2: Pattern Mining (90 min, ~$0.50)
1. **Spawn agent-pattern-miner** (Haiku, max_turns=10)
   - Task: Analyze top 100 successful sessions
   - Extract common patterns
   - **Output**: `/tmp/success_patterns.json`

2. **Spawn agent-antipattern-hunter** (Haiku, max_turns=10)
   - Task: Analyze failed/high-token sessions
   - Identify anti-patterns
   - **Output**: `/tmp/antipatterns.json`

3. **Spawn agent-tool-analyst** (Haiku, max_turns=8)
   - Task: Tool usage correlation analysis
   - **Output**: `/tmp/tool_recommendations.json`

**Run in parallel**: 3 agents × ~$0.15-0.20 = ~$0.50 total

**Deliverables**: Pattern library (success + anti-patterns)

### Wave 3: Alignment Measurement (60 min, ~$0.25)
1. **Score all prompts** (Haiku batch job)
   - Characteristics: specificity, complexity, directiveness
   - Process in batches of 50

2. **Generate alignment report** (Local Python + Haiku summary)
   - Success rates by archetype
   - Token efficiency metrics
   - Failure mode taxonomy
   - **Output**: `concepts/model-alignment-metrics.md`

**Deliverables**: Comprehensive alignment scoreboard in vault

### Wave 4: COHESION Integration (120 min, $0)
1. **Implement MCP tool** (`analyze_prompt_effectiveness()`)
   - Add to Cloud Vault MCP
   - Wire up Ollama + SurrealDB
   - Test with 10 sample prompts

2. **Update agent personas** (`patterns/bmad-agent-persona-definition.md`)
   - Add "Preferred Prompt Patterns" section
   - Document anti-patterns

3. **Create runbook** (`patterns/runbook-prompt-optimization.md`)
   - How to use `analyze_prompt_effectiveness()`
   - Best practices from pattern mining
   - Examples of good vs bad prompts

**Deliverables**: Production-ready meta-learning system

## Success Metrics

### Immediate (End of Wave 3)
- ✅ 647 prompts indexed, embedded, classified
- ✅ 10-15 success patterns identified
- ✅ 5-8 anti-patterns documented
- ✅ Alignment scoreboard in vault
- ✅ Tool usage recommendations

### Medium-term (2 weeks post-deployment)
- 🎯 20% reduction in prompt rework iterations
- 🎯 15% improvement in token efficiency
- 🎯 `analyze_prompt_effectiveness()` used 50+ times
- 🎯 2-3 agent personas refined with new patterns

### Long-term (1 month)
- 🎯 Continuous learning loop operational (daily updates)
- 🎯 30% of prompts run through pre-flight analysis
- 🎯 Pattern library grows to 25+ success patterns
- 🎯 Measurable improvement in task completion rates

## Economics

| Phase | Agent Type | Est. Tokens | Est. Cost | Time |
|-------|-----------|-------------|-----------|------|
| Wave 1: Setup | Local Python + Ollama | 0 | $0.00 | 30 min |
| Wave 2: Mining | 3× Haiku (parallel) | ~200K | $0.50 | 90 min |
| Wave 3: Alignment | Haiku batch + local | ~100K | $0.25 | 60 min |
| Wave 4: Integration | Local dev (no AI) | 0 | $0.00 | 120 min |
| **TOTAL** | | **~300K** | **$0.75** | **300 min (5 hrs)** |

**vs Human Analysis**: ~40 hours × $150/hr = $6,000 (8000x more expensive)

**vs Claude-only (Sonnet)**: ~900K tokens × $0.003 = $2.70 (3.6x more expensive)

## Risks & Mitigations

### Risk 1: Debug logs may not contain full conversation content
**Mitigation**: Focus on extractable metrics (tokens, tools, outcomes) rather than full transcript analysis. If needed, add logging to future sessions.

### Risk 2: 647 prompts may be too small for robust patterns
**Mitigation**: Start with high-confidence patterns (5+ examples). Expand dataset over time with continuous learning loop.

### Risk 3: SurrealDB query performance at scale
**Mitigation**: Start with 647 prompts (trivial scale). Benchmark at 5K, 50K. Add vector indexing if needed.

### Risk 4: Ollama embeddings may differ from Claude's internal representations
**Mitigation**: Use embeddings for clustering/similarity only. Rely on Haiku for qualitative analysis where semantic understanding matters.

## Alternatives Considered

### Alt 1: Manual Log Review (Human)
- **Cost**: 40 hours × $150/hr = $6,000
- **Quality**: Deep insights but subjective
- **Scalability**: Doesn't scale to continuous learning
- **Verdict**: ❌ Too expensive, not repeatable

### Alt 2: Claude-only Analysis (All Sonnet)
- **Cost**: ~$2.70 (3.6x more)
- **Quality**: High
- **Scalability**: Good
- **Verdict**: ⚠️ More expensive, but viable if Haiku quality insufficient

### Alt 3: Full ML Pipeline (Classical NLP)
- **Cost**: $0 (local sklearn/spacy)
- **Quality**: Lower (no semantic understanding)
- **Complexity**: High (feature engineering, model training)
- **Verdict**: ❌ Over-engineered for 647 samples

### Alt 4: No Analysis (Status Quo)
- **Cost**: $0
- **Quality**: N/A
- **Learning**: Zero
- **Verdict**: ❌ Misses opportunity to improve COHESION

## Decision

**Proceed with proposed architecture** (4-wave execution plan).

**Rationale**:
1. **Token-efficient**: Leverages Ollama ($0) + Haiku ($0.75) vs Sonnet ($2.70+)
2. **Proven patterns**: Builds on successful Kyutai/Sheets Bridge agent coordination
3. **Actionable**: Delivers MCP tool for immediate use
4. **Scalable**: Continuous learning loop grows insights over time
5. **Compound engineering**: Feeds back into COHESION agent orchestration

**Next Steps**:
1. Create Wave 1 indexer script
2. Extend SurrealDB schema
3. Spawn Wave 2 mining agents (3 parallel Haiku)
4. Review outputs, proceed to Wave 3-4

## References

- Proven pattern: [[google-sheets-vault-bridge]] (batch Haiku agents)
- Proven pattern: [[automated-concept-extraction]] (Ollama embeddings)
- Infrastructure: [[mcp-infrastructure-architecture]]
- Similar work: [[2026-02-10-kyutai-pocket-tts-token-efficient-success|Kyutai Phase 4 Performance Benchmarking]] (agent metrics)

## Related - [[prompt-engineering]]
- [[mcp-model-context-protocol]]
Concepts

- [[token-efficiency]] — Economic optimization driving architecture choices
- [[compound-engineering]] — Knowledge accumulation methodology this system extends
- [[agentic-ai]] — Agent-based pattern mining approach
- [[context-management]] — Relevant to log context window analysis

## Related Lessons

- [[lesson-11-team-agent-efficiency]] (operational validation)

- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]] (operational validation)

  - [[lesson-17-stale-branch-mining]] (validation relevance: 13)
  - [[lesson-34-test-hang-unmocked-live-service]] (validation relevance: 13)
  - [[lesson-16-pre-commit-hooks-stage-override]] (validation relevance: 13)
  - [[lesson-37-experience-guided-execution-works-new]] (validation relevance: 13)
  - [[lesson-38-singleton-executor-for-sessions-new]] (validation relevance: 13)

## Related Patterns

- [[log-lifecycle-management]] — the log lifecycle pattern implementing the mining pipeline architecture decided here
- [[log-rotation-and-monitoring]] — the log rotation and retention pattern that supports the log mining data flow

## Related Concepts

- [[emu3-multimodal-next-token-prediction]]
- [[3d-graph-plugin-selection]]
- [[2026-02-09-ollama-context-management]]
- [[2026-02-12-claude-code-context-awareness-codification]]
- [[2026-02-12-charter-aligned-scoring-formula]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance]]
