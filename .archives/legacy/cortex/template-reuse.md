---
title: "Template Reuse"
date: "2026-02-10"
tags: [concept, methodology, efficiency, patterns]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 7
  synapse_out: 11
---

## Definition

**Template reuse** is the practice of copying working implementations as starting points for new projects, rather than building from scratch. In compound engineering, templates capture proven patterns in executable form, reducing token spend by 87-98% while maintaining quality.

## The Copy vs Build Economics

### Build From Scratch
```
Research (10-20K tokens) → Design (5-10K tokens) → Implement (20-40K tokens) → Test (5-10K tokens)
Total: 40-80K tokens, 8-16 hours
```

### Copy Template
```
Copy files (0 tokens) → Customize (2-5K tokens) → Test (1-2K tokens)
Total: 3-7K tokens, 1-2 hours
```

**Savings**: 87-98% tokens, 85-90% time

## Why Templates Compound

### Traditional Code Reuse (Libraries)
- Import library → Use functions
- **Benefit**: Code reuse (don't rewrite sorting algorithms)
- **Limitation**: Fixed interface, can't modify internals

### Template Reuse (Full Project Patterns)
- Copy entire project → Modify freely
- **Benefit**: Architecture + implementation + tests + docs
- **Advantage**: Full control, no external dependencies
- **Compound effect**: Each copy learns from previous copies

## Cohezion's Template Library

### 1. cloud-vault-mcp (FastMCP Server Template)

**Original cost**: 40K tokens (initial development)
**Copy cost**: 500 tokens (copy files + customize config)
**Savings**: 79x efficiency (40K → 500 tokens)

**What's included**:
- FastMCP server boilerplate (server.py, dependencies)
- 7 tool examples (vault_read, vault_write, etc.)
- Test suite structure (pytest, mocks, fixtures)
- Configuration patterns (pyproject.toml, uv.lock)
- Documentation structure (README.md)

**Use when**: Building any new MCP server

**Customization points**:
- Add new tools (100-200 tokens each)
- Modify existing tools (50-100 tokens)
- Update config (50 tokens)

### 2. ollama-mcp (Local Model Management Template)

**Original cost**: 20K tokens (Phase 1 implementation)
**Copy cost**: 300 tokens (copy + customize)
**Savings**: 67x efficiency

**What's included**:
- Ollama API client wrapper (ollama_client.py)
- Model selection logic (task → model mapping)
- Context management (token counting, chunking)
- 5 tool patterns (query, embed, batch, status, select_model)
- Test suite (80 tests, 100% coverage)

**Use when**: Building tools that need local LLM inference

### 3. Haiku Research Agent Pattern

**Original cost**: 15K tokens (initial workflow design)
**Copy cost**: 200 tokens (spawn agent with proven config)
**Savings**: 75x efficiency

**What's included**:
- Agent configuration (model=haiku, max_turns=5-10)
- JSON output format (structured results)
- Web search pattern (query → extract → validate)
- Batch coordination pattern (4 parallel agents)

**Use when**: Bulk web research, API documentation lookup

### 4. Sheets Pipeline Template

**Original cost**: 25K tokens (original pipeline)
**Copy cost**: 400 tokens (adapt to new sheet)
**Savings**: 62x efficiency

**What's included**:
- SheetsBridge integration (batch read/write)
- Work queue pattern (SQLite state machine)
- Agent coordination (parallel Haiku agents)
- Error handling (retry logic, DLQ)
- Result extraction (JSON from JSONL)

**Use when**: Bulk data processing with Google Sheets

## Template Discovery Process

### How to Identify Template Candidates

**Criteria**:
1. **Reuse frequency**: Used 3+ times already (proven pattern)
2. **Broad applicability**: Solves common problem (MCP servers, research, pipelines)
3. **Stable interface**: Core structure unlikely to change
4. **Self-contained**: Minimal external dependencies

**Examples**:
- ✅ FastMCP server pattern (used by cloud-vault-mcp, ollama-mcp, kyutai-mcp)
- ✅ Haiku research agent (used in sheets pipeline, concept extraction, paper enrichment)
- ❌ Specific business logic (unique per project, not reusable)
- ❌ Experimental patterns (unstable, might change)

### Template Extraction Process

1. **Identify working implementation** (already exists in codebase)
2. **Generalize** (replace specific names with placeholders)
3. **Document** (README with customization points)
4. **Test** (ensure template itself works)
5. **Store** (version control + vault documentation)

**Time**: 2-4 hours
**Cost**: 10-20K tokens
**ROI**: 5x after 2 copies, 50x after 10 copies

## Template Maintenance

### Versioning Strategy

**Semantic versioning for templates**:
- **Major (v2.0.0)**: Breaking changes (incompatible with v1.x)
- **Minor (v1.1.0)**: New features (backwards compatible)
- **Patch (v1.0.1)**: Bug fixes (no new features)

**Example**: cloud-vault-mcp
- v1.0.0: Initial FastMCP pattern
- v1.1.0: Added streaming support
- v1.2.0: Added async/await patterns
- v2.0.0: Migrated to new MCP protocol

### Update Propagation

**Challenge**: If template improves, existing copies don't auto-update

**Strategies**:
1. **Document divergence**: Each copy tracks its template version
2. **Selective backport**: Copy valuable improvements back to original
3. **No forced updates**: Copies own their destiny (independence > consistency)

**Example**: ollama-mcp added context caching (v1.1.0). cloud-vault-mcp may or may not adopt (depends on need).

## Copy-Customize Workflow

### Step-by-Step

```bash
# 1. Copy template (0 tokens, 30 seconds)
cp -r cloud-vault-mcp new-project-mcp
cd new-project-mcp

# 2. Customize config (100 tokens, 2 minutes)
# pyproject.toml: name, description, version
# README.md: project-specific docs

# 3. Implement ONE new feature (2-5K tokens, 30-60 minutes)
# src/server.py: add new tool
# tests/test_new_tool.py: add tests

# 4. Validate (1-2K tokens, 10-20 minutes)
pytest tests/ -v  # All tests pass?
# Manual test: Does new tool work?

# 5. Document divergence (200 tokens, 5 minutes)
# README.md: "Based on cloud-vault-mcp v1.2.0"
# CHANGELOG.md: What changed from template
```

**Total**: 3-7K tokens, 1-2 hours (vs 40-80K tokens, 8-16 hours from scratch)

## Anti-Patterns

### 1. Reinventing the Wheel

**Symptom**: Building from scratch when template exists
- "I'll create a new MCP server from scratch" (40K tokens)
- Available: cloud-vault-mcp template (500 tokens to copy)
- **Waste**: 39.5K tokens (79x inefficiency)

**Example**: [[2026-02-10-kyutai-token-waste-postmortem]]
- Researched from scratch (10K tokens)
- Ignored cloud-vault-mcp template
- Result: 61K tokens, 0% functional output

**Fix**: ALWAYS check for templates before starting new projects

### 2. Template Overgeneralization

**Symptom**: Making template so generic it's unusable
- 50 configuration options (paralysis)
- 20 abstract classes (over-engineered)
- **Result**: Harder to use than building from scratch

**Example**: Java Spring Boot templates (often over-engineered)

**Fix**: Keep templates concrete, document customization points, optimize for 80% use case

### 3. Copy Without Understanding

**Symptom**: Copy template but don't understand it
- Template has security flaw → All copies have flaw
- Template uses deprecated API → All copies break when API removed
- **Risk**: Compound failures across all copies

**Fix**: Read template code before copying, understand key patterns, validate security

### 4. No Template Updates

**Symptom**: Original improves, but no copy benefits
- Template v1.0: Basic functionality
- Template v2.0: 3x faster, better error handling
- Copies: Still on v1.0 (missed improvements)

**Fix**: Track template version in each copy, periodically review for valuable updates

## Relationship to Other Concepts

**Template reuse is the tactical execution layer**:

- [[compound-engineering]]: Philosophy (accumulate reusable knowledge)
- [[meta-learning]]: Strategic layer (learn which patterns to template)
- [[roi-analysis]]: Measurement layer (template ROI = 5x → 50x)
- **Template reuse**: Tactical layer (actually copy and use the templates)

**Flow**:
1. Work on project (compound engineering)
2. Identify reusable pattern (meta-learning)
3. Measure reuse frequency (roi-analysis)
4. Extract template if ROI >5x (template reuse)
5. Copy template for future projects (tactical execution)

## Metrics

### Template Effectiveness

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Copy frequency** | 3+ copies/month | Active template |
| **Token savings** | >80% reduction | Copy cost vs build cost |
| **Time savings** | >75% reduction | Copy time vs build time |
| **Customization cost** | <20% of build cost | Low overhead |
| **Success rate** | >90% | Copies that reach production |

### Cohezion Template Stats

| Template | Copies | Avg Savings | Total Saved | ROI |
|----------|--------|-------------|-------------|-----|
| **cloud-vault-mcp** | 3 | 39.5K tokens | 118.5K tokens | 2.96x |
| **ollama-mcp** | 2 | 19.7K tokens | 39.4K tokens | 1.97x |
| **Haiku research agent** | 8 | 14.8K tokens | 118.4K tokens | 7.9x |
| **Sheets pipeline** | 1 | 24.6K tokens | 24.6K tokens | 0.98x |
| **Total** | 14 | — | 300.9K tokens | **13.8x** |

**Insight**: Haiku agent has highest ROI (highest copy frequency × moderate savings)

## Primary Sources

- Hunt, A., & Thomas, D. (1999). *The Pragmatic Programmer*. Addison-Wesley. — DRY principle (Don't Repeat Yourself)
- [[2026-02-10-kyutai-token-waste-postmortem]] — Case study: Template blindness costs 39.5K tokens
- [[implementation-first-infrastructure-later]] — Templates as validated implementations

## Related Concepts

- [[compound-engineering]] — Methodology that template reuse supports
- [[token-efficiency]] — Templates as token optimization strategy (87% savings)
- [[meta-learning]] — Learning which patterns to template
- [[roi-analysis]] — Measuring template ROI (5x → 50x)

## Relevance to Cohezion

Template reuse is **critical** for Cohezion's token efficiency. With 12+ agents building MCP servers, research pipelines, and integrations, copying proven patterns (500 tokens) instead of researching from scratch (40K tokens) creates 79x efficiency gains.

The [[2026-02-10-kyutai-token-waste-postmortem]] demonstrates the cost of template blindness: 61K tokens spent researching/building what cloud-vault-mcp already provided. With template reuse, that project would cost 8K tokens (500 copy + 7.5K customize) instead of 61K—an 87% savings.

**Core principle**: Copy working implementations, customize minimally, validate quickly. Template reuse is [[implementation-first-infrastructure-later]] applied at project scale.

---

*Extracted from: [[2026-02-10-meta-pattern-extraction]] session*
*Validated by: 87-98% token savings across 14 template copies*

## Daily References

- [[SESSION-62-PHASE-3-COMPLETE-FINAL-SUMMARY]]
- [[2026-02-14-wave-1-status-snapshot]]
- [[2026-02-14-phase-7-preparation-complete]]
- [[2026-02-14-phase-7-execution-complete]]

## Skills

- adaptive_template_engine — Template-driven development patterns
- ADAPTIVE_TEMPLATE_PRIME — Adaptive template evolution
- skill_generator — Skill scaffolding from templates
- TEMPLATE_DRIVEN_DEVELOPMENT_PRIME — Template-driven development methodology
