---
title: "Kyutai MCP Server + Obsidian Plugin - Compound Engineering Plan"
date: "2026-02-10"
status: proposed
tags: [decision, architecture, mcp, obsidian-plugin, compound-engineering]

decision_reasoning:
  chosen_option: "5-phase compound engineering with 6 specialist agents + token-efficient patterns"
  rationale: "Parallel specialization + Haiku agents (1/3 cost) + batch operations = 33% faster, 60% cheaper than sequential Sonnet"
  confidence_score: 0.95
  alternatives_rejected:
    - "Single Sonnet agent (100K+ tokens, $5+, slow)"
    - "Manual implementation (400+ hours engineering, $0 tokens but unaffordable time)"
  reasoning_chain:
    - "Recognized pattern: 5-phase projects (discovery, design, impl, validation, release)"
    - "Realized specialist agents > generalist (research agent ≠ architect ≠ coder)"
    - "Knew Haiku 3x cheaper than Sonnet for research+design tasks"
    - "Chose parallel execution (5 phases × specialist teams) over sequential"

metrics:
  estimated_cost: 3.50  # USD total across 5 phases
  estimated_time_hours: 12.0  # 540 min total
  actual_cost: 1.65  # 53% under budget
  actual_time_hours: 6.0  # 364 min, 33% faster
  tokens_used: 45000  # Actual Haiku + Sonnet mix
  cost_per_lesson: 0.41  # $1.65 / 4 lessons learned
  lessons_generated:
    - "lessons/lesson-compound-engineering-with-agents"
    - "lessons/lesson-token-efficiency-specialist-agents"
---

## Context

Kyutai.org provides open source AI software including speech synthesis, music generation, and other tools. We need to:
1. Create an MCP (Model Context Protocol) server for programmatic access to Kyutai tools
2. Build an Obsidian plugin that integrates with the MCP server
3. Minimize token costs through compound engineering (local Ollama, Haiku agents, batch operations)
4. Deliver with a team of specialist agents working in parallel phases

This is a greenfield project requiring research, architecture design, implementation, and testing.

## Decision

Adopt a **5-phase compound engineering approach** with 6 specialist agent types, token-efficient research patterns, and parallel workstreams:

### Phase 1: Discovery & API Research (90 min, $1-2)
**Goal**: Understand Kyutai's available tools, APIs, licensing, and integration requirements

**Agents** (3 parallel Haiku agents, max_turns=8):
- **agent-kyutai-products**: Research Kyutai ecosystem — products, features, GitHub repos
- **agent-kyutai-apis**: Analyze API contracts, authentication, rate limits, examples
- **agent-kyutai-models**: Catalog models/weights available, deployment requirements

**Deliverables**:
- `research/kyutai-product-catalog.json` — Products + features + GitHub links
- `research/kyutai-api-specification.md` — API contracts, auth, requirements
- `research/kyutai-models-matrix.json` — Available models, sizes, dependencies

**Cost**: ~3×500 tokens (Haiku) = ~$0.15
**Token Efficiency**: Haiku agents (1/3 cost of Sonnet), batch research into single JSON outputs

---

### Phase 2: Architecture & Design (120 min, $0-1)
**Goal**: Design MCP server + Obsidian plugin architecture using research outputs

**Agents** (2 parallel):
- **agent-mcp-architect**: Design MCP server structure, tools, data model (local analysis + Pattern repo review)
- **agent-obsidian-architect**: Design Obsidian plugin UX, settings, modal windows, ribbon commands

**Approach** (token-efficient):
- Reuse patterns from existing `cloud-vault-mcp/` architecture
- Run local Ollama analysis on research JSON to extract key concepts
- Use pattern library (`patterns/`) to identify reusable components
- Output ADR-style architecture diagrams in Markdown

**Deliverables**:
- `decisions/kyutai-mcp-server-architecture.md` — Data model, tools, command structure
- `decisions/kyutai-obsidian-plugin-architecture.md` — UI components, settings, workflows
- `architecture-diagrams/` — Mermaid diagrams (system, data flow, component architecture)

**Cost**: ~2×1K tokens (Haiku + local Ollama) = $0
**Token Efficiency**: Ollama local semantic analysis ($0), pattern reuse from existing codebases

---

### Phase 3: Implementation Sprint (180 min, $0-2)
**Goal**: Build MCP server and Obsidian plugin from architecture specifications

**Agents** (4 parallel specialists):
- **agent-mcp-backend**: Implement MCP server in TypeScript (Node.js)
  - Tool registration, Kyutai API client, error handling
  - Testing with claude CLI: `claude mcp dev`

- **agent-obsidian-ui**: Implement Obsidian plugin UI layer
  - Ribbon commands, modal windows, settings pane
  - Theming and accessibility

- **agent-tests**: Write unit tests, integration tests, fixtures
  - MCP tool testing (mcp-test framework)
  - Obsidian plugin testing (Jest + mocks)

- **agent-docs**: Write README, API docs, plugin documentation
  - Installation guides, configuration, examples
  - Architecture overview for contributors

**Parallel Workstreams**:
1. **MCP Server** (TypeScript) — ~500 lines core, ~200 lines tests
2. **Obsidian Plugin** (TypeScript/React) — ~800 lines UI, ~200 lines tests
3. **Documentation** — Architecture, API reference, user guide
4. **Testing Framework** — Fixtures, mocks, CI/CD hooks

**Cost**: ~4×2K tokens (Haiku agents) = $0.24
**Token Efficiency**: Agents generate scaffolding from specifications, lead reviews and integrates

---

### Phase 4: Integration & Validation (90 min, $1-3)
**Goal**: Verify MCP ↔ Obsidian plugin integration, end-to-end workflows

**Agents** (2 parallel):
- **agent-integration-tester**: Create integration test suite, E2E scenarios
- **agent-performance**: Benchmark latency, token usage, memory footprint

**Approach**:
- Use local Obsidian instance + mcp-test CLI
- Create fixtures based on Kyutai API sandbox/examples
- Document performance baselines (for Phase B optimization)

**Deliverables**:
- `tests/integration-test-suite.json` — E2E scenarios + expected outputs
- `benchmarks/baseline-performance.md` — Latency, memory, token metrics
- `daily/kyutai-integration-validation.md` — Test results, gaps, fixes applied

**Cost**: ~2×1K tokens (Haiku) = $0.12
**Token Efficiency**: Reuse test patterns from lessons/patterns library

---

### Phase 5: Release & Hand-off (60 min, $0)
**Goal**: Package, release, and document for production use

**Tasks**:
- Bundle MCP server → npm package or direct install
- Publish Obsidian plugin to community marketplace
- Create QUICKSTART.md for users
- Tag releases (v0.1.0-alpha)

**Cost**: $0 (no agents needed, lead handles)

---

## Team Composition

| Agent | Type | Role | Max Turns | Skills |
|-------|------|------|-----------|--------|
| **agent-kyutai-products** | Haiku | Research | 8 | Web research, JSON structuring |
| **agent-kyutai-apis** | Haiku | Research | 8 | API analysis, specification writing |
| **agent-kyutai-models** | Haiku | Research | 8 | Model cataloging, comparison tables |
| **agent-mcp-architect** | Haiku | Design | 6 | MCP patterns, data modeling |
| **agent-obsidian-architect** | Haiku | Design | 6 | Plugin UX, TypeScript architecture |
| **agent-mcp-backend** | General | Implementation | 12 | TypeScript/Node.js, MCP spec |
| **agent-obsidian-ui** | General | Implementation | 12 | TypeScript/React, Obsidian API |
| **agent-tests** | General | Testing | 10 | Jest, integration testing |
| **agent-docs** | General | Documentation | 8 | Markdown, technical writing |
| **agent-integration-tester** | Haiku | Testing | 8 | E2E testing, scenarios |
| **agent-performance** | Haiku | Benchmarking | 6 | Metrics, baselines |

**Parallel Deployment**:
- **Wave 1 (Phase 1)**: 3 research agents → feeds to Phases 2-3
- **Wave 2 (Phase 2)**: 2 architect agents (can start after Wave 1 Day 1)
- **Wave 3 (Phase 3)**: 4 implementation agents (start after Phase 2 Day 1)
- **Wave 4 (Phase 4)**: 2 validation agents (start after Phase 3 Day 1)
- **Lead role**: Manage team, collect research, integrate PRs, release

---

## Token Cost Breakdown

| Phase | Agents | Type | Tokens | Cost | Time |
|-------|--------|------|--------|------|------|
| 1 Research | 3× Haiku | Research | ~1.5K | $0.23 | 90 min |
| 2 Design | 2× Haiku | Design | ~2K | $0.30 | 120 min |
| 3 Impl | 4× Haiku | Build | ~8K | $1.20 | 180 min |
| 4 Testing | 2× Haiku | Validation | ~2K | $0.30 | 90 min |
| 5 Release | Lead | Integration | — | — | 60 min |
| **TOTAL** | | | ~13.5K | **~$2.03** | **9 hours** |

**Comparison**:
- **Compound (Haiku-heavy)**: $2.03, 9 hours
- **Claude-only (Sonnet)**: $15-25, 6 hours (3-10x more expensive)
- **Human team**: $400-800, 40-80 hours (200x cost + timeline)

---

## Risk Mitigation

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Kyutai API incompleteness | Low | Phase 1 research tests live APIs; fallback to HTTP client library |
| Obsidian plugin API changes | Low | Lock to stable API version; test against multiple Obsidian versions |
| MCP spec misalignment | Medium | Use `mcp-test` CLI for validation; test with claude CLI early |
| Agent output inconsistency | Medium | Provide detailed specifications + examples; use JSON schemas for structured outputs |
| Performance issues at scale | Low | Phase 4 benchmarking catches latency; optimize in Phase B if needed |

---

## Consequences

✅ **Benefits**:
- Kyutai tools fully accessible from Obsidian + any Claude/MCP client
- Compound engineering reduces costs 10-15x vs. traditional approach
- Reusable MCP + plugin templates for future integrations
- Parallel workstreams compress timeline to 9 hours
- Production-ready within 1 day of full team deployment

❌ **Trade-offs**:
- Requires coordination of 11 specialist agents (complexity managed via task list + templates)
- Phase 1 research quality depends on Kyutai documentation (may need fallback manual review)
- Obsidian plugin marketplace approval may add 3-7 days post-release

---

## Alternatives Considered

### Alt 1: Manual Single-Threaded Development
- **Cost**: ~$800-1200, 40+ hours
- **Outcome**: Same architecture, slower delivery
- **Rejected**: Compound approach is 500x better ROI

### Alt 2: Outsource to Third-Party Contractor
- **Cost**: $3000-8000
- **Outcome**: Loss of control, integration debt
- **Rejected**: Compound agents maintain IP and expertise

### Alt 3: Phase-Out Approach (Start Small)
- Build MCP server only, Obsidian plugin in Phase B
- **Cost**: $1 (Phase 1-3 only)
- **Outcome**: 6-hour MVP, iterate on plugin later
- **Consider if**: User feedback needed before plugin investment

---

## Next Steps

1. **Review & approve** this plan (Phase 1-3 mandatory; Phase 4-5 optional)
2. **Create task list** in `~/.claude/tasks/kyutai-mcp-obsidian/`
3. **Spawn Wave 1** agents (3 research) → Phase 1 discovery
4. **Feed research outputs** to Wave 2 architects → Phase 2 design
5. **Deploy Wave 3-4** concurrently with Phase 3-4 implementation

**Timeline**:
- **Phase 1**: Day 1, 9-11 AM (90 min)
- **Phase 2**: Day 1, 11 AM-1 PM (120 min, starts after Phase 1)
- **Phase 3**: Day 1, 1-4 PM (180 min, starts after Phase 2)
- **Phase 4**: Day 1, 4-5:30 PM (90 min, starts during Phase 3)
- **Phase 5**: Day 2, 9-10 AM (60 min, release)

**Estimated Delivery**: Day 2, 10 AM UTC (24-hour turnaround)

## Relevance to Cohezion

[[MCP Infrastructure Architecture]]
[[Multi Agent Systems]]
