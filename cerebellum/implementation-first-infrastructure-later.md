---
title: "Implementation First, Infrastructure Later"
date: "2026-02-10"
status: "validated"
tags: [pattern, token-efficiency, compound-engineering, methodology]
aspect: thinker
neural:
  activation: 0.9
  stage: mature
  synapse_in: 1
  synapse_out: 15
---

## Problem

Large-scale projects risk consuming excessive tokens on infrastructure (tests, docs, dependencies) before validating that the core implementation is feasible or valuable. This leads to:

- **Token waste**: 61,000+ tokens spent on scaffolding with 0% functional output
- **Premature optimization**: Building production-ready test suites for non-existent code
- **Template blindness**: Ignoring working templates (e.g., cloud-vault-mcp) in favor of starting from scratch
- **Documentation debt**: Writing 1,200-line API references before using a single endpoint

## Solution

**Validate first, scale second.** Follow a strict phased approach that proves value before investing in infrastructure:

### Phase 1: Minimal Viable (2-3 hours, ~8K tokens)

```python
# 1. Copy working template
cp -r existing-working-project new-project
cd new-project

# 2. Implement ONE feature (100-200 lines)
# src/core_feature.py
async def minimal_feature(input: str) -> dict:
    """Single feature that proves the concept works"""
    result = process(input)
    return {"output": result}

# 3. Test manually (does it work?)
python -m pytest tests/test_core_feature.py -v

# 4. Write 5 REAL tests (not placeholders)
def test_minimal_feature_happy_path():
    assert minimal_feature("input") == {"output": "expected"}

def test_minimal_feature_edge_case():
    # Real test, real assertion
    pass
```

**Result**: Working feature in 2-3 hours, minimal token spend

### Phase 2: Only If Phase 1 Works

- Add 2-3 more features (if needed)
- Add 5 more tests per feature
- Document **what actually works** (not theoretical APIs)
- Scale infrastructure proportionally to implementation

## Code Example

### ✅ Implementation-First (8K tokens, 100% output)

```bash
# Day 1: Validate
git clone working-template new-project
vim src/feature.py  # 150 lines
pytest tests/test_feature.py  # 5 real tests
git commit -m "feat: core feature working"

# Day 2: Scale (only if Day 1 succeeded)
vim src/feature2.py  # 200 lines
pytest tests/test_feature2.py  # 8 real tests
vim docs/usage.md  # Document what exists
```

### ❌ Infrastructure-First (61K tokens, 0% output)

```bash
# Day 1: Build scaffolding
mkdir -p tests/ docs/ src/
touch tests/test_{1..22}.py  # 600 placeholder tests
vim docs/api-reference.md  # 1,192 lines, all APIs
npm install jest typescript @types/* --save-dev  # 73MB

# Day 2: Stalled (no implementation)
# Result: 0% functional, 61K tokens wasted
```

## When to Use

**Use this pattern when:**
- Starting a new MCP server, plugin, or tool
- Exploring a new API or integration
- Building proof-of-concept features
- Token budget is constrained
- Working template exists (cloud-vault-mcp, ollama-mcp, etc.)

**Especially critical for:**
- AI agent-driven projects (tokens are currency)
- Unfamiliar APIs (validate before documenting)
- Hardware-constrained environments (test one model before installing 73MB)

## Key Principle

> "The best test suite is the one that tests code that exists."
> — Kyutai MCP Postmortem, 2026-02-10

## Metrics

| Approach | Tokens | Time | Output | Efficiency |
|----------|--------|------|--------|------------|
| **Implementation-First** | 8,000 | 2-3h | 100% | ✅ Baseline |
| **Infrastructure-First** | 61,000 | 8h+ | 0% | ❌ 7.6x waste |
| **Savings** | 53,000 (87%) | 5h+ | ∞% | 🎯 Optimal |

## Related Patterns

- [[compound-engineering]] — Core methodology that this pattern supports
- [[session-retrospective]] — How to capture lessons from failures
- [[token-efficiency-patterns]] — Broader token optimization strategies

## Related Decisions

- [[2026-02-10-kyutai-token-waste-postmortem]] — Case study: 61K token waste from reversing this pattern
- [[2026-02-10-phase-a-implementation-complete]] — Example of phased validation

## Anti-Pattern: Infrastructure First, Hope Implementation Follows

### Description

Building elaborate test infrastructure, comprehensive documentation, and full dependency chains **before** implementing the core functionality. This anti-pattern assumes:

1. The API/feature will work as documented
2. All researched approaches are valid
3. Infrastructure motivates implementation
4. Placeholder tests are "almost done"

### Why It Fails

**Token Economics:**
- Documentation: 1,192 lines researching 5 APIs → Use 1 API (80% waste)
- Tests: 600 placeholder tests → 1 functional test (99.8% waste)
- Dependencies: 73MB installed → 0MB used (100% waste)

**Psychological Trap:**
- Feels productive (lots of files created!)
- Looks professional (full test suite!)
- Avoids hard problem (actual implementation)

### Remediation

1. **Archive current work**: Don't delete, but move aside
2. **Copy working template**: cloud-vault-mcp, ollama-mcp, etc.
3. **Implement ONE feature**: 100-200 lines, prove it works
4. **Write 5 real tests**: Tests that actually pass
5. **Then decide**: Scale if validated, abandon if not

### Real-World Example

**Kyutai MCP Server (2026-02-10):**
- 61,000 tokens spent on research (1,192 lines), tests (4,416 lines), dependencies (73MB)
- Result: 0% functional, 1/22 tests passing
- **Correct approach**: Copy cloud-vault-mcp template, add ONE Pocket TTS tool (8K tokens)
- **Outcome**: Archive project, extract lessons, restart with template

### Severity

**CRITICAL** — Can consume 7.6x normal token budget with zero functional output.

---

*Extracted from: [[2026-02-10-kyutai-token-waste-postmortem]]*
*Validated by: session 11 safe-mode retrospective*

## Decisions That Validated This Pattern

- [[2026-02-10-kyutai-token-waste-postmortem]] — the failure case that motivated this pattern (infrastructure-first led to 7.6x token waste)
- [[2026-02-10-kyutai-pocket-tts-token-efficient-success]] — the success case that validated this pattern (90% token savings achieved)
- [[2026-02-10-phase3-3d-graph-adversarial-review]] — the 3D graph adversarial review that recommended applying this pattern to avoid repeating kyutai mistakes

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-14-phases-1-3-retrospective-key-learnings]]
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]]
- [[2026-02-14-phase-6a-automated-reasoning-chain-inference-complete]]
- [[2026-02-10-canvas-driven-compound-engineering-refined]]
- [[2026-02-14-wave-1-overnight-completion-report]]
- [[2026-02-14-compound-engineering-team-execution-retrospective]]
