---
title: "Entire.io API Investigation & Integration Design"
date: 2026-02-11
status: in-progress
tags: [experiment, entire-io, integration, daemon, research-lineage]
---

# Entire.io API Investigation & Integration Design

## Executive Summary

Entire.io is enabled in manual-commit mode. It stores checkpoint metadata in git commit messages with structured session summaries. The daemon will:
1. Poll git log for new commits containing entire.io checkpoint data
2. Extract session metadata (summary, metrics, timestamp)
3. Map to agent session/decision/outcome schema
4. Sync to vault notes and SurrealDB for research lineage queries

## Findings

### 1. Entire.io Current Status

**Configuration**: Manual-commit mode enabled
```
vault/.entire/settings.json:
{
  "strategy": "manual-commit",
  "enabled": true
}
```

**Checkpoint Storage**: Git commit metadata
- Stored in commit message body (after "Entire: " marker)
- Contains: session summary, metrics, timestamps, outcomes
- Example: `31a250a` contains vault metrics, team status, project summary

**Available Commands**:
- `entire status` - Show enabled/disabled status
- `entire explain [flags]` - Explain sessions/commits/checkpoints
- `entire enable/disable` - Toggle integration
- `entire reset/resume/rewind/doctor` - Session management

**Missing Command**: No direct `entire commit` API (must use git log parsing)

### 2. Data Structure Analysis

Example checkpoint commit metadata:
```
commit 31a250afe8511e22934be5db6b857a8350ce84c2
Author: Mike Anderson <mike@example.com>
Date: Mon Feb 9 23:55:18 2026 -0500

docs: COHEZION checkpoint - 90% vault coverage, multiple projects executing

Session Summary (2026-02-10):
✅ Completed semantic linking via Claude Sonnet (78%→90% coverage)
✅ SurrealDB sync: 33 new links imported to 12D graph
✅ Adversarial review: 4 agents exposed plan flaws, saved 00+
✅ Kyutai Phase 3: 4 builders actively implementing MCP+plugin
✅ Sheets pipeline: Production-ready daemon, awaiting deployment
✅ 3D Graph: Deployed with 181-link semantic data

Vault Metrics:
- Papers: 87% (73/84)
- Decisions: 88% (15/17)
- Patterns: 95% (18/19)
- Concepts: 100% (22/22)
- Experiments: 100% (2/2)
- TOTAL: 90% (130/144)

Team: 14+ agents across 5 concurrent projects
Status: 🟢 ACCELERATING
Next: Phase B optimization + Kyutai Phase 4 + Sheets deployment

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

**Extractable Fields**:
1. **Timestamp**: `CommitDate` from git metadata
2. **Session Summary**: Bulleted list of outcomes/completions
3. **Metrics**: Structured vault metrics (papers %, decisions %, etc.)
4. **Team Status**: Agents deployed, concurrent projects
5. **Next Actions**: Planned work from status line

### 3. Integration Architecture

#### Data Flow
```
git log --since
    ↓
Parse commit metadata (checkpoints only)
    ↓
Extract: timestamp, summary, metrics, outcomes
    ↓
Map to SurrealDB schema:
  - agent_session (from commit author + timestamp)
  - agent_decision (from summary bullets)
  - agent_outcome (from metrics + status)
    ↓
Vault sync:
  - Create daily/checkpoint-{date}.md notes
  - Link to relevant decisions/patterns/concepts
    ↓
SurrealDB sync:
  - Create relationships
  - Calculate metrics
  - Update 12D graph dimensions
```

#### Implementation Pattern

Reuse `sheets_research_daemon.py` pattern:
1. **WorkQueue** (SQLite): Track processed commits by SHA
2. **AsyncIO polling**: Check `git log --since={last_check}`
3. **DLQ**: Failed commits (unparseable, missing data)
4. **Batch operations**: Vault + SurrealDB updates per cycle
5. **Graceful shutdown**: Signal handlers + state persistence

**New Components**:
- `entire_ops.py`: Extract and transform entire.io metadata
- `entire_sync_daemon.py`: Polling + queuing + sync orchestration
- `entire_main.py`: CLI entry point (status, dlq, retry, etc)

### 4. Challenges & Mitigations

| Challenge | Mitigation |
|-----------|-----------|
| No official API for checkpoint access | Use git log parsing (reliable, git is SCM source of truth) |
| Unstructured commit body format | Heuristic parsing (regex bullets, metrics sections) + fallback to raw |
| Session authorship from git commits | Map git author to agent_id (may need config file for aliases) |
| Async commit availability (eventual consistency) | Use git log directly (available immediately on local) |
| Checkpoint timestamp vs commit timestamp | Use CommitDate (when authored), not AuthorDate (when created) |
| Missing parsed transcript | Extract summary only (sufficient for Phase 1) |

### 5. Phase 1 Scope (Weeks 1-2)

**MVP**: Extract session summaries + metrics from commits

**In Scope**:
- Parse commit timestamps + authors
- Extract bulleted outcomes from commit body
- Extract structured metrics (papers %, total %)
- Map to agent_session nodes (timestamp, author, status)
- Create daily checkpoint notes in vault
- Basic error handling + DLQ for unparseable commits

**Out of Scope** (Phase 2-3):
- Full transcript parsing (requires `entire explain --raw-transcript` integration)
- Bidirectional sync (vault → git commits)
- Advanced agent reasoning extraction
- Real-time streaming (batch polling sufficient for now)

### 6. Query Examples (Once Schema Live)

#### Query 1: Session Timeline
```surql
SELECT
  agent_session.{id, agent_id, start_time, status, outcome_summary},
  <-results_in<-agent_outcome.metrics
FROM agent_session
WHERE start_time >= 2026-02-01
ORDER BY start_time DESC
```

#### Query 2: Metrics Trends
```surql
SELECT
  agent_session.{id, start_time},
  agent_outcome.metrics.total_vault_coverage,
  agent_outcome.metrics.paper_coverage
FROM agent_session
WHERE start_time >= 2026-02-01
ORDER BY start_time ASC
```

#### Query 3: Team Workload
```surql
SELECT
  agent_session.agent_id,
  count(*) as session_count,
  avg(agent_outcome.metrics.decisions_made) as avg_decisions
FROM agent_session
WHERE start_time >= 2026-02-01
GROUP BY agent_id
ORDER BY session_count DESC
```

## Implementation Plan

### Step 1: Entire.io Ops Module (1.5h)
- Create `entire_ops.py` with metadata extraction
- Heuristic parsing for bullets + metrics
- Logging + error handling

### Step 2: Daemon Skeleton (1.5h)
- Copy `sheets_research_daemon.py` pattern
- Adapt polling logic for git log
- WorkQueue + DLQ for commits

### Step 3: Vault Sync (1h)
- Daily checkpoint note creation
- Linking to existing notes
- Frontmatter metadata

### Step 4: SurrealDB Sync (1.5h)
- Agent session node creation
- Decision/outcome extraction from summaries
- Edge creation for relationships

### Step 5: Testing + Deployment (1.5h)
- Unit tests for parsing
- Integration test with live git repo
- Systemd unit + runbook

**Total**: 7 hours (can parallelize with Phase 1 Steps 3-4)

## Risks & Mitigations

1. **Parsing brittleness**: Commit format variations
   - Mitigation: Test against multiple commit formats, flexible regex

2. **Performance**: Large git histories
   - Mitigation: Index commits by date, use git log --since, cache processed SHAs

3. **Duplicate processing**: Same commit processed twice
   - Mitigation: WorkQueue tracks SHA, idempotent operations

4. **Missing agent metadata**: Git author ≠ agent_id
   - Mitigation: Config file with author→agent mappings

## Success Criteria

- [ ] Parse 5+ different commit formats without failures
- [ ] Extract metrics with 90%+ accuracy
- [ ] Process 100 commits in <30 seconds
- [ ] DLQ recovery rate >95%
- [ ] Integration test: Sync vault + SurrealDB in single cycle
- [ ] Zero breaking changes to existing tools

## Related

**Concepts**: [[Entire.io Integration]], [[Research Lineage]], [[Agent Context Tracking]]

**Decisions**: [[2026-02-11-entire-io-integration-architecture]], [[2026-02-11-use-event-driven-daemon-for-entire-io]]

**Patterns**: [[Event-Driven Daemon Pattern]], [[SurrealDB Sync Pattern]]

**Projects**: [[Phase 1 - SurrealDB Agent Context Schema]], [[Week 1 - Entire.io Integration]]

## Related Concepts

- [[2026-02-13-track-b-entire-sync-daemon-complete]]
- [[2026-02-09-fastmcp-asgi-integration-fix]]
- [[2026-02-13-phase-2-track-b-entire-io-sync-daemon-complete]]
- [[2026-02-14-graphrag-verification-and-integration-session]]
- [[entire-io-to-vault-mapping]]
- [[runbook-entire-sync-daemon]]
- [[entire-io-sync-daemon-design]]
- [[entire-io-sync-daemon-operations]]
