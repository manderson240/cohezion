---
title: "Claude Code Context Awareness Codification"
date: 2026-02-12
status: proposed
tags: [decision, governance, claude-code, platform-health]
---

## Context

Claude Code sessions are operating with suboptimal context awareness:
- Best practices communicated verbally, not encoded
- Tool selection happens ad-hoc rather than systematically
- Mistakes repeat because patterns aren't captured as executable procedures
- New agents/sessions don't inherit platform knowledge

**Current state:** PRIME governance framework exists but Claude Code practices aren't formalized.

**Goal:** Make the platform self-defending by encoding Claude Code best practices into executable procedures + automated guidance.

## Decision

Implement **3-layer codification** to increase context awareness and prevent uninformed mistakes:

### Layer 1: Policy (CLAUDE.md Enhancement)
Update `/home/mike-anderson/vaults/cohezion-vault/CLAUDE.md` to add:
- **Tool Selection Criteria** — When to use Read/Edit/Glob/Grep vs Bash
- **Parallel Execution Guidelines** — When independent tools can run together
- **Agent Delegation Triggers** — Conditions for spawning Explore/Plan agents
- **Token Budget Strategies** — Usage patterns for remaining 66% budget
- **MCP Tool Awareness** — Cloud Vault MCP + Ollama capabilities

### Layer 2: Procedure (PRIME_CLAUDE_CODE_PRACTICES Skill)
Create a PRIME skill that encodes:
- **Metadata**: Version, author, charter alignment, applicability
- **Concepts**: 6 core concepts (tool-selection, parallel-execution, delegation, memory, mcp-integration, git-safety)
- **Instructions**: 12 procedural rules with decision trees
- **Examples**: 4-5 real scenarios from past sessions
- **Evolution History**: Track improvements as lessons emerge
- **Validation**: Checklist for operators to verify implementation
- **Charter Alignment**: Link to Constitution principles

**Format:** Reusable template (2,500 tokens, 10:1 ROI as established in Task #9)

### Layer 3: Metrics & Observability
Create decision log entries tracking:
- **Adoption rate**: % of sessions following procedures
- **Mistake prevention**: Categorized mistakes avoided (tool-selection, git-safety, parallel-execution, etc.)
- **Context awareness improvement**: Session-to-session knowledge retention
- **Agent performance**: Speed improvements from tool selection + parallelization
- **Memory ROI**: Value gained from encoded knowledge vs token cost

Track in `daily/` logs with structured metrics for downstream analysis.

## Implementation Plan (5 steps, 2-3 hours)

### Step 1: CLAUDE.md Enhancement (30 min)
Add 4 new sections with decision criteria + examples:
- Tool selection matrix (Read, Edit, Glob, Grep, Bash, Write)
- Parallelization checklist
- Agent delegation flowchart
- Token budget breakdown + strategy

**Files**: `CLAUDE.md` (add ~800 lines)
**Validation**: Read by all subsequent agents ✓

### Step 2: PRIME_CLAUDE_CODE_PRACTICES Skill (60 min)
Create reusable governance procedure:
- Template: 7-section PRIME structure
- Concepts: Tool selection, parallelization, delegation, memory, MCP, git-safety
- Instructions: 12 procedural rules with decision trees
- Examples: 5 real scenarios (tool-selection mistakes, successful parallelization, agent delegation)
- Evolution: Track improvements over 3 months
- Validation: 6-point checklist for operators

**Files**: `patterns/PRIME_CLAUDE_CODE_PRACTICES.md` (2,500 LOC)
**Format**: Markdown + YAML frontmatter for MCP indexing

### Step 3: Integration with MCP (15 min)
Enable agents to discover the skill automatically:
- Index in Cloud Vault MCP skill registry
- Make discoverable via `query_skills` tool
- Test via `/PRIME_CLAUDE_CODE_PRACTICES` invocation

**Files**: Cloud Vault MCP skill_index.json
**Validation**: Query returns skill with full context ✓

### Step 4: Initial Adoption Tracking (30 min)
Create daily metrics template:
- Sessions applying skill procedures
- Mistakes prevented (categorized)
- Tool-selection efficiency gains
- Parallelization performance improvements
- Memory reuse rate

**Files**: `daily/_claude-code-metrics-2026-02-12.md` (template)
**Owners**: Session leads assign metrics responsibility

### Step 5: Validation & Sign-Off (15 min)
6-point checklist:
- [ ] CLAUDE.md updated with all 4 sections + examples
- [ ] PRIME skill created + indexed in MCP
- [ ] 3 agents tested skill discovery workflow
- [ ] Metrics template validated + tracked
- [ ] Memory updated with procedure links
- [ ] Decision signed off (status: accepted)

## Why This Works

**Compounding Knowledge**:
- Policy layer (CLAUDE.md) → humans read once, context persists
- Procedure layer (PRIME skill) → agents reference automatically
- Metrics layer → tracks real-world impact, informs evolution

**Self-Defending Platform**:
- New agents inherit best practices automatically
- Mistakes caught early via decision trees in PRIME skill
- Memory system compounds improvements across sessions
- 10:1 ROI: 2,500 tokens per skill → eliminates 25K tokens of repeated mistakes

**Charter Alignment**:
- Links to Constitution principles (S01: Intentionality, S02: Execution Excellence)
- Governance becomes autonomous (no manual intervention needed)
- Scales with team size without overhead

## Alternatives Considered

### A. Embed guidance in system prompt only
**Rejected**: Not visible to users, can't evolve, no metrics tracking

### B. Create separate documentation file
**Rejected**: Not indexed, not discoverable, not executable

### C. PRIME skill approach (CHOSEN)
**Advantages**:
- Indexed by MCP
- Discoverable + executable
- Evolves with metrics feedback
- 10:1 ROI established
- Charter-aligned

## Metrics (Expected)

**Implementation Cost**: 2-3 hours
**Ongoing Cost**: 15 min/week (metrics tracking)
**Expected ROI**:

| Metric | Baseline | Target | Timeline |
|--------|----------|--------|----------|
| Tool-selection mistakes avoided | 3/session | 0.5/session | 1 month |
| Parallelization adoption | 10% | 60% | 2 weeks |
| Memory reuse rate | 20% | 70% | 1 month |
| Agent context awareness | Baseline | +40% | 2 weeks |
| Mistake categories prevented | 0 | 5+ | 1 month |

## Next Steps

1. Assign Layer 1 (CLAUDE.md) — 30 min
2. Assign Layer 2 (PRIME skill) — 60 min
3. Test MCP indexing — 15 min
4. Track metrics for 2 weeks
5. Iterate PRIME skill based on metrics feedback

## Charter Alignment

- **S01** (Intentionality): Codified best practices encode explicit intention
- **S02** (Execution Excellence): Procedures automate quality checks
- **S05** (Observability): Metrics track real-world impact
- **S06** (Compound Engineering): Knowledge layers compound over time

---

**Owner**: Platform Lead
**Timeline**: 2026-02-12 to 2026-02-13
**Dependencies**: None (can execute in parallel with Phase 2 tracks)
**Approved**: Pending user sign-off
