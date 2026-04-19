---
title: "Agent Logs Vault Schema: Storing Entire.io Execution Context"
date: 2026-02-11
tags: [pattern, schema, vault, agent-context, entire.io]
status: active
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 7
  synapse_out: 24
---

## Problem

Entire.io captures comprehensive agent execution context (decisions, actions, outcomes). To integrate this into our vault and enable post-hoc analysis, we need:

1. A structured way to store agent execution summaries
2. Ability to link back to decisions and lessons
3. Easy retrospective access to execution context
4. Automatic note generation from agent work

## Solution

**Store agent execution as daily summaries in `daily/agent-logs/`**, treating them as operational ephemera that fuel human retrospectives.

### Directory Structure

```
vault/
└── daily/
    ├── _template.md                 ← Template for agent logs
    ├── agent-logs/                  ← Auto-generated summaries
    │   ├── 2026-02-11T14-30-sess-abc123.md
    │   ├── 2026-02-11T15-45-sess-def456.md
    │   └── 2026-02-12T09-15-sess-ghi789.md
    ├── 2026-02-11-daily-standup.md
    └── 2026-02-10-retrospective.md
```

### Frontmatter Schema

Agent logs use extended YAML frontmatter beyond regular daily notes:

```yaml
---
date: "2026-02-11T14:30:00Z"
title: "Agent Execution Summary - sess-abc12345"
tags: [agent, execution, entire.io]
status: archived
source: entire.io
session_id: "sess-abc12345"
agent_names: [researcher, implementer, tester]
---
```

**Field Descriptions**:

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| **date** | ISO datetime | When session occurred | "2026-02-11T14:30:00Z" |
| **title** | string | Human-readable title | "Agent Execution Summary - sess-abc12345" |
| **tags** | array | Categorization | [agent, execution, entire.io] |
| **status** | string | Note lifecycle | "archived" (immutable after creation) |
| **source** | string | Data origin | "entire.io" |
| **session_id** | string | Unique session identifier | "sess-abc12345" |
| **agent_names** | array | Participating agents | [researcher, implementer, tester] |

**Design Rationale**:
- `status: archived` prevents accidental editing (session is immutable once recorded)
- `source: entire.io` enables filtering for other data sources (manual, other services)
- `session_id` links back to SurrealDB records
- `agent_names` enables filtering by team member

### Note Structure

Each agent log contains standard sections:

#### 1. Execution Summary (Required)

```markdown
## Execution Summary

**Duration**: 5342ms
**Status**: completed
**Model**: haiku
**Turns**: 47
**Functions**: 312
```

Records session-level metrics from entire.io. Used for:
- Quick performance assessment
- Cost tracking (model × turns → tokens)
- Error rate analysis

#### 2. Key Decisions (Optional)

```markdown
## Key Decisions

- [[surrealdb]] - Provides native graph edges for research lineage queries
- [[Defer daemon implementation to Week 2]] - Validate Phase 1 schema first
```

Wiki-links to decisions created during this session. Shows:
- Which vault decisions were made
- Why they were made (via the link)
- When they were made (date stamp)

**Source**: SurrealDB `decision` records with `session_id` match

#### 3. Context Shifts (Optional)

```markdown
## Context Shifts

- Task: Feature A → Task: Feature B
- Model: Haiku → Sonnet (for complex reasoning)
- Owner: Agent A → Agent B
```

Records significant context changes that affected decision-making. Useful for:
- Understanding why decisions changed
- Identifying context switching costs
- Detecting external blockers

#### 4. Extracted Learnings (Optional)

```markdown
## Extracted Learnings

- [[implementation-first-infrastructure-later]] - Severity: CRITICAL (auto-extracted)
- [[surrealdb]] - Severity: HIGH (auto-extracted)
- [[lesson-surrealdb-schema-design]] - Severity: MEDIUM (human-added)
```

Lessons validated or discovered during this session:
- Auto-extracted: Identified by system from session transcript
- Human-added: Curator notes from retrospective
- Links to `lessons/` vault directory for permanent storage

**Source**: SurrealDB `lesson` records linked to session outcomes

#### 5. Session Artifacts (Optional)

```markdown
## Session Artifacts

- [[2026-02-09-12d-graph-surrealdb-integration]]
- [[agent-logs-vault-schema]]
- [[2026-02-11-graphrag-proof-of-concept-success]]
```

Direct links to notes created during this session. Enables:
- Quick access to session output
- Vault-wide traceability (notes linked back to session)
- Aggregation of multi-session projects

#### 6. Related Research (Optional)

```markdown
## Related Research

- [[surrealdb-graph-databases]] - Informed decision on database choice
- [[schema-design-relational]] - Influenced schema decisions
```

Papers consulted during research phase. Shows:
- Research lineage (what informed decisions)
- Knowledge gaps (what wasn't available)
- Source credibility assessment

**Source**: SurrealDB `relates_to_paper` edges from session

#### 7. Metrics & Performance (Required)

```markdown
## Metrics & Performance

{
  "total_turns": 47,
  "total_functions": 312,
  "errors": 2,
  "recovery_attempts": 1
}
```

Structured metrics for:
- Performance analysis
- Cost tracking
- Error rate trends
- Recovery efficiency

---

## Implementation Details

### Daemon Integration (Week 2)

`entire_sync_daemon.py` will:

1. Poll entire.io API for completed sessions
2. Fetch session metadata + related context
3. Generate markdown using template
4. Write to `daily/agent-logs/YYYY-MM-DDTHH-MM-ss-{session_id}.md`
5. Create SurrealDB records simultaneously
6. Link vault notes back to session

**Batch processing**:
- Process 200-300 sessions/day
- Batch write every 50 sessions or 5 minutes
- Error recovery with DLQ

### Lifecycle Management

**Retention Policy**:

| Age | Status | Action |
|-----|--------|--------|
| < 7 days | active | Human review possible |
| 7-30 days | archived | Extractable for lessons/patterns |
| > 30 days | retired | Move to archive, keep SurrealDB |

**Retrospectives**:

1. Daily: Quick scan at end of day (5 min)
2. Weekly: Aggregate learnings (30 min)
3. Monthly: Extract patterns + update lessons (2h)

**Archiving**:

```bash
# Move old summaries to archive after 30 days
find daily/agent-logs -mtime +30 -exec mv {} daily/archive/ \;
```

---

## File Format Example

**Filename**: `2026-02-11T14-30-sess-abc12345.md`

```markdown
---
date: "2026-02-11T14:30:00Z"
title: "Agent Execution Summary - sess-abc12345"
tags: [agent, execution, entire.io]
status: archived
source: entire.io
session_id: "sess-abc12345"
agent_names: [researcher, implementer, tester]
---

## Execution Summary

**Duration**: 5342ms
**Status**: completed
**Model**: haiku
**Turns**: 47
**Functions**: 312

## Key Decisions

- [[surrealdb]] - Provides native relationship edges for research lineage queries
- [[surrealdb]] - Prevents rework on Week 2

## Context Shifts

- Task: Phase 1 Schema → Task: Phase 1 Integration
- Model: Haiku (initial) → Sonnet (complex decisions)

## Extracted Learnings

- [[implementation-first-infrastructure-later]] - Severity: CRITICAL (auto-extracted)
- [[mcp-infrastructure-architecture]] - Severity: HIGH (auto-extracted)

## Session Artifacts

- [[2026-02-11-phase-1-agent-context-schema-complete]]
- [[agent-logs-vault-schema]]

## Related Research

- [[surrealdb-graph-databases]] - Informed database decision
- [[knowledge-graphs-semantic-web]] - Influenced relationship design

## Metrics & Performance

{
  "total_turns": 47,
  "total_functions": 312,
  "errors": 2,
  "recovery_attempts": 1
}

## Session ID

`sess-abc12345`
```

---

## When to Use This Pattern

✅ **Use agent-logs for**:
- Agent execution tracking
- Post-hoc session analysis
- Research lineage recording
- Lesson validation evidence
- Team performance metrics

❌ **Don't use agent-logs for**:
- Permanent knowledge (extract to `decisions/`, `patterns/`, `lessons/` instead)
- Individual action logs (too granular)
- Real-time monitoring (use entire.io dashboard)
- Manual task tracking (use `daily/` template instead)

---

## Integration with Other Schemas

### Relationship to Daily Notes

```
daily/_template.md
  ├── Human-authored daily standup
  └── Links to agent-logs for context

daily/agent-logs/_template.md (THIS SCHEMA)
  ├── Auto-generated from entire.io
  ├── Linked from daily retrospectives
  └── Sources vault decisions/lessons

decisions/2026-02-11-*.md
  ├── Created during agent execution
  ├── Linked from agent-logs
  └── Permanent vault record

lessons/2026-02-11-*.md
  ├── Extracted from session outcomes
  ├── Linked from agent-logs
  └── Knowledge base entry
```

### Relationship to SurrealDB

```
entire.io (source)
    ↓
SurrealDB (structured graph)
  ├── session record
  ├── decision records
  ├── outcome records
  └── lesson records
    ↓
Vault (human-readable)
  ├── daily/agent-logs/*.md (note)
  ├── decisions/*.md (permanent)
  ├── lessons/*.md (permanent)
  └── patterns/*.md (permanent)
```

---

## Querying Agent Logs

### Find sessions by agent

```obsidian
tag:#agent
agent_names:researcher
```

### Find sessions with high error rates

```obsidian
tag:#agent
status:archived
errors:>3
```

### Find lessons extracted this week

```obsidian
tag:#agent
date:2026-02-07..2026-02-13
Extracted Learnings:*
```

### Find sessions related to a topic

```obsidian
tag:#agent
Related Research:papers/surrealdb*
```

---

## Best Practices

### For Daemon Authors (Week 2)
- Use template variables exactly as specified
- Always set `status: archived` immediately
- Include all metrics, even if 0
- Create agent-logs before dashboard updates SurrealDB
- Handle rate limiting (200-300 sessions/day max)

### For Curators (Retrospectives)
- Add wiki-links to decisions/lessons found during review
- Update `Extracted Learnings` section with human insights
- Mark important sessions with priority comment
- Move valuable insights to permanent categories

### For Researchers
- Filter by date range for trend analysis
- Use session_id to cross-reference SurrealDB
- Extract metrics for reporting
- Link insights back to session for traceability

---

## Validation Checklist

Before daemon writes notes, validate:

- [ ] Frontmatter has all 8 required fields
- [ ] date is ISO 8601 format
- [ ] session_id is non-empty
- [ ] agent_names is valid array
- [ ] status is always "archived"
- [ ] All wiki-links resolve in vault
- [ ] Metrics JSON is valid
- [ ] Duration values are numeric (milliseconds)
- [ ] No secrets in Execution Summary
- [ ] No stack traces in extracted learnings

---

## Related Decisions & Patterns

- [[decision-vault-first-knowledge-architecture]] - Why vault is primary store
- [[pattern-implementation-first-infrastructure-later]] - Design methodology
- [[pattern-compound-engineering]] - How agent work compounds knowledge
- [[lesson-effective-retrospectives]] - Conducting session retrospectives

---

**Last Updated**: 2026-02-11
**Status**: Active (ready for daemon implementation)
**Next Review**: 2026-02-13 (after Phase 1 completion)

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-11-phase-1-agent-context-schema-complete]]
- [[2026-02-12-phase-2-schema-design]]
- [[2026-02-11-surrealdb-agent-context-schema-design]]
- [[entire-io-to-vault-mapping]]
- [[automated-concept-extraction]]
- [[sheetsbr idge-mcp-testing]]
- [[phase1-production-validation-runbook]]
- [[agent-logs-schema-validation]] — pre-commit validation checklist that enforces this schema before writing to vault
