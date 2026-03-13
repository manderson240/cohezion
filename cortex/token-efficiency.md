---
title: "Token Efficiency"
date: "2026-02-10"
tags: [concept, methodology, ai-engineering, economics]
related_concepts: [token-efficiency-patterns, compound-engineering, meta-learning, context-management, machine-learning-optimization]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 122
  synapse_out: 26
---

## Definition

**Token efficiency** is the optimization of Large Language Model (LLM) token consumption to maximize functional output per token spent. In AI-assisted engineering, tokens are currency — every API call, agent task, and research query has a token cost that compounds across projects.

## The Economics

### Token as Currency

Unlike traditional compute resources, LLM tokens have both **cost** and **context** implications:

- **Cost**: API pricing is per-token (input + output)
- **Context**: Each token consumes limited context window space
- **Compound effect**: Poor efficiency scales linearly with project count

### Baseline Metrics

| Model | Cost per 1M tokens | Typical task | Token count | Task cost |
|-------|-------------------|--------------|-------------|-----------|
| **Claude Haiku** | $0.25 / $1.25 (in/out) | Web research | 15-20K | $0.025-0.035 |
| **Claude Sonnet** | $3.00 / $15.00 (in/out) | Code implementation | 40-60K | $0.50-0.75 |
| **Claude Opus** | $15.00 / $75.00 (in/out) | Complex reasoning | 80-120K | $2.50-4.00 |
| **Local Ollama** | $0.00 | Embeddings, classification | Unlimited | $0.00* |

*Hardware cost not included

## Key Principles

### 1. Validate Before Scaling

**Pattern**: [[implementation-first-infrastructure-later]]

Prove a concept works with minimal tokens before investing in infrastructure:
- ✅ 8K tokens → Working feature → Scale if validated
- ❌ 61K tokens → Full infrastructure → Discover feature doesn't work

### 2. Use the Right Model for the Job

**Haiku for research** (1/3 cost of Sonnet):
- Web searches, API documentation lookups
- JSON extraction, structured data processing
- Quick validations, status checks

**Sonnet for implementation** (balanced):
- Code writing, architecture design
- Complex debugging, refactoring
- Production-quality output

**Opus for reasoning** (5x Sonnet cost):
- Multi-step planning, strategic decisions
- Novel problem-solving, research synthesis
- Only when Sonnet insufficient

### 3. Template Reuse Over Reinvention

Copying working templates costs ~500 tokens. Building from scratch costs 8,000-60,000 tokens:
- **cloud-vault-mcp**: FastMCP server with 7 tools, working tests
- **ollama-mcp**: Model management with context handling
- **Haiku research agents**: Proven web research patterns

### 4. Batch Operations

Single operations compound linearly. Batch operations amortize overhead:
- ❌ Update 100 rows sequentially: 100 API calls, ~5,000 tokens each = 500K tokens
- ✅ Batch update 100 rows: 10 batches, ~8,000 tokens each = 80K tokens (84% savings)

### 5. Local-First Processing

When Ollama works (embeddings, classification, simple reasoning), use it:
- **Cost**: $0 API tokens (electricity ~$0.01-0.05/hour)
- **Privacy**: No data leaves local machine
- **Speed**: No network latency for inference

**Caveat**: Context management and prompt engineering still consume human time.

## Anti-Patterns

### Infrastructure-First Development

Building scaffolding before implementation:
- **Example**: 1,192-line API docs + 600 placeholder tests before writing code
- **Cost**: 61,000 tokens, 0% functional output
- **Remediation**: [[implementation-first-infrastructure-later]]

### Model Mismatches

Using expensive models for simple tasks:
- ❌ Opus for JSON extraction: $4.00
- ✅ Haiku for JSON extraction: $0.03 (133x cheaper)

### Sequential Agent Work

Spawning 20 agents sequentially (wait for each to finish):
- **Time**: 20 × 3 minutes = 60 minutes
- **Tokens**: 20 × 15K = 300K tokens
- ✅ **Better**: Spawn 4 parallel batches of 5 agents = 15 minutes

### Over-Research

Researching every possible approach before picking one:
- **Example**: 5 API endpoints documented, 1 actually used (80% waste)
- **Fix**: Document-as-you-go (implement → document → repeat)

## Case Studies

### Success: Sheets Research Pipeline

**Approach**: Haiku agents (4 parallel) with batch updates
- **Cost**: $1.36 per 560 rows researched
- **Time**: 42 minutes end-to-end
- **Output**: 100% functional, vault notes + sheet updates

**Why it worked**:
- Right model (Haiku for web research)
- Parallelization (4 agents at once)
- Batch operations (SheetsBridge batch API)
- Proven template (reused research agent pattern)

### Failure: Kyutai MCP Server (Initial)

**Approach**: Infrastructure-first with comprehensive research
- **Cost**: 61,000 tokens
- **Time**: 8+ hours
- **Output**: 0% functional (1/22 tests passing)

**What went wrong**:
- Researched 5 APIs, documented all, used none
- Wrote 600 placeholder tests before implementation
- Installed 73MB dependencies before validating need
- Ignored working template (cloud-vault-mcp)

**Recovery**: Restarted with template, built ONE feature first (8K tokens)

### Success: 12D Graph Phase 2

**Approach**: Local Ollama for embeddings + Haiku for gap analysis
- **Cost**: $0.00 API tokens
- **Time**: 10 minutes
- **Output**: 84 papers with embeddings, conceptual depth, research gaps

**Why it worked**:
- Local-first (Ollama embeddings = $0)
- Right scope (semantic dimensions only, not full graph)
- Incremental (Phase 1 → Phase 2 → Phase 3)

## Metrics to Track

### Per-Project Metrics

- **Token spend**: Total input + output tokens
- **Token efficiency**: Functional LOC per 1K tokens
- **Model mix**: % Haiku / Sonnet / Opus / Local
- **Rework rate**: Tokens spent on discarded work

### Portfolio Metrics

- **Average cost per feature**: Trend over time (should decrease)
- **Template reuse rate**: % projects using templates vs from-scratch
- **Agent utilization**: Sequential vs parallel work
- **Batch operation adoption**: % operations batched vs sequential

## Tools & Patterns

- [[implementation-first-infrastructure-later]] — Validate before scaling
- [[session-retrospective]] — Capture token waste lessons
- [[google-sheets-vault-bridge]] — Batch operations pattern
- **Haiku research agents**: Proven pattern for web research (max_turns=5-10)
- **Ollama MCP**: Local inference for embeddings, classification

## Relationship to Compound Engineering

Token efficiency amplifies [[compound-engineering]]'s compounding effect:

- **Session 1**: Spend 60K tokens, learn nothing → Next session starts from zero
- **Session 1 (efficient)**: Spend 8K tokens, document lessons → Next session reuses templates, spends 5K tokens

Over 100 sessions:
- **Inefficient path**: 100 × 60K = 6M tokens (~$1,500)
- **Efficient path**: 8K + 99 × 5K = 503K tokens (~$75) — **12x ROI**

## Primary Sources

- Anthropic (2026). *Claude Pricing*. [https://www.anthropic.com/pricing](https://www.anthropic.com/pricing) — Current token pricing
- OpenAI (2025). *Token Optimization Best Practices*. [https://platform.openai.com/docs/guides/optimization](https://platform.openai.com/docs/guides/optimization)
- [[2026-02-10-kyutai-token-waste-postmortem]] — Case study: 61K token waste

## Navigation

- [[MOC-compound-engineering]] — Map of Content for compound engineering, sessions, retrospectives, and token efficiency

## Related Concepts

- [[compound-engineering]] — Core methodology
- [[context-management]] — Related to token context windows
- [[agentic-ai]] — Agent-based token consumption patterns
- [[sustainable_ai]] — token efficiency reduces the environmental cost of AI-assisted development
- [[optimizations]] — token-level optimizations parallel model-level optimization techniques (caching, batching, routing)
- [[2026-02-10-phase3a-3d-graph-validation|Phase 3A: 3D Graph Validation]] — demonstrated 98.6% token savings by validating with existing plugin before building custom (500 tokens vs 35K)
- [[2026-02-16-fix-3-reasoning-inference-option-b|Fix #3: Reasoning Inference Option B]] — chose the token-efficient option (2 hours vs 3-4 days) for reasoning inference
- [[2026-02-19-token-limit-error-prevention-implemented|Token Limit Error Prevention]] — implements concrete safeguards (calculate_max_tokens, auto-retry with reduction) against token limit errors

- [[pattern-implementation-first-infrastructure-later]] — the implementation-first pattern directly reduces token waste by avoiding premature infrastructure investment

## Related Lessons

- [[lesson-11-team-agent-efficiency]] — CRITICAL: team coordination overhead (2-5K tokens per handoff) directly impacts token costs; single agents are token-efficient for tasks under ~2 hours
- [[lesson-29-batch-cache-two-phase]] — batch cache two-phase pattern delivers 60% reduction in compute costs; amortizes token overhead across batch operations
- [[lesson-adversarial-review-before-execution]] — adversarial review prevents wasted token spend; 45x ROI (5K tokens of review prevents 225K tokens of wasted execution)

## Related from Patterns & Projects

- [[honest-time-tracking-all-costs]] — honest time tracking reveals true token-per-feature cost, enabling accurate efficiency measurement
- [[research-pipeline-mission-2026-02-26]] — Haiku agents with batch updates keep per-row cost under $0.01, demonstrating token-efficient pipeline design

## Relevance to Cohezion

Token efficiency is critical for Cohezion's agent orchestration model. With 12+ agents potentially running in parallel, poor token efficiency would make projects economically infeasible. The [[implementation-first-infrastructure-later]] pattern, combined with Haiku-first research and local Ollama processing, keeps per-project costs under $5 while maintaining production quality.

---

*Extracted from: [[2026-02-10-kyutai-token-waste-postmortem]]*
*Validated by: Multiple project retrospectives (Sheets Pipeline, 12D Graph, Kyutai phases)*

## Daily References

- [[2026-02-09-token-efficiency-retrospective]] — token efficiency and compound engineering retrospective: 46% budget used, 3 major infrastructure components delivered
- [[2026-02-10-COHEZION-STATUS-CHECKPOINT]] — Cohezion status checkpoint with vault health at 90% semantic coverage and 14+ agents deployed

## Missions

- [[research-pipeline-2026-02-26]] — Batch processing 900 rows across five agent teams demonstrating token-efficient pipeline design

## Session References

- [[SESSION-43-PHASE-6-LAUNCH]] — CostAwareRouter cost/token optimization achieving 100% cost reduction on local models
- [[SESSION-46-COMPLETE]] — cost analytics framework tracking and optimizing token spending
- [[session-50-handoff]] — 35-40% cost reduction cascade from FLUME embedding optimization
- [[SESSION-50-QUICKSTART]] — quick-start activation of 35-40% cost reduction via optimized encoder

## Agent Outputs

- **Adversarial Review: Compound Engineering Agent Swarm** — `Agents/Antigravity/42233b97-45f7-4a48-bd44-7a7be04e48c9/adversarial_review.md`
- **Walkthrough: Token-Efficient Compound Engineering** — `Agents/Antigravity/42233b97-45f7-4a48-bd44-7a7be04e48c9/walkthrough.md`
- **Token Efficient Compound Engineering Enhancements** — `Agents/Antigravity/469087d9-f08d-418d-8826-250eab85acf0/task.md`

## Skills

- BATCHING_PROTOCOL_PRIME — Token waste reduction via batching
- caching — Cache-based performance optimization
- LOCAL_OFFLOAD_PRIME — Token efficiency via local SLM offloading
- MODEL_ROUTING_PRIME — Token cost trade-offs in routing
- QUARTER_ON_A_STRING_PRIME — Token efficiency and resource orchestration
- SEMANTIC_CACHING_PRIME — Reducing redundant LLM calls
- THROTTLED_SCOUT_PRIME — Load shedding for token efficiency
- TOKEN_EFFICIENCY_PRIME — Token consumption optimization
- USAGE_ANALYTICS_PRIME — Resource allocation optimization
