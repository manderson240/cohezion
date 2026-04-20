---
title: "Entire.io to Vault Agent Logs Mapping Guide"
date: 2026-02-11
tags: [pattern, integration, entire.io, entire-sync-daemon]
status: active
aspect: thinker
neural:
  activation: 0.98
  stage: mature
  synapse_in: 12
  synapse_out: 15
---

## Overview

This guide maps entire.io output format to vault `daily/agent-logs/` schema for Week 2 daemon implementation.

**Purpose**: `entire_sync_daemon.py` reads entire.io API responses and generates valid agent log markdown files.

---

## Entire.io Output Format

### Hypothetical API Response Structure

```json
{
  "session": {
    "id": "sess-abc12345",
    "start_timestamp": "2026-02-11T14:30:00Z",
    "end_timestamp": "2026-02-11T14:45:22Z",
    "duration_ms": 9480000,
    "status": "completed",
    "agents": [
      {
        "name": "researcher",
        "model": "haiku",
        "turns": 12,
        "functions": 24
      },
      {
        "name": "implementer",
        "model": "haiku",
        "turns": 11,
        "functions": 23
      }
    ],
    "metrics": {
      "total_turns": 23,
      "total_functions": 47,
      "errors": 0,
      "recovery_attempts": 0
    },
    "context": {
      "shifts": [
        "Task: Research → Task: Implementation",
        "Model: Haiku → Haiku (consistent)"
      ]
    },
    "decisions": [
      {
        "id": "dec-001",
        "timestamp": "2026-02-11T14:32:15Z",
        "title": "Use SurrealDB for agent context",
        "reasoning": "Native graph edges enable research lineage",
        "alternatives": ["PostgreSQL", "MongoDB"],
        "chosen": "SurrealDB",
        "reversible": true
      }
    ],
    "outcomes": [
      {
        "status": "success",
        "summary": "Schema and service layer implemented",
        "artifacts": [
          "agent_context_schema.sql",
          "agent_context_ops.py"
        ]
      }
    ],
    "lessons": [
      {
        "title": "Implementation-first methodology",
        "severity": "CRITICAL",
        "description": "Validate concept with minimal code before scaling",
        "auto_extracted": true
      }
    ]
  }
}
```

---

## Field Mapping Matrix

### Session-Level Mapping

| Entire.io Field | Vault Frontmatter | Mapping Rule | Notes |
|-----------------|-------------------|--------------|-------|
| session.id | session_id | Direct copy | Used for SurrealDB linkage |
| session.start_timestamp | date | ISO format, use start time | Timezone should be Z (UTC) |
| session.agents[*].name | agent_names | Array of agent names | Extract from agents list |
| session.duration_ms | Execution Summary | Direct copy | Keep in milliseconds |
| session.status | Execution Summary | Direct copy | completed \| error \| running |
| session.agents[0].model | Execution Summary | Primary agent's model | For cost tracking |
| session.agents[*].turns | Execution Summary | Sum all agents | total_turns = sum(agent.turns) |
| session.agents[*].functions | Execution Summary | Sum all agents | total_functions = sum(agent.functions) |
| session.metrics | Metrics & Performance | Direct copy | All fields mapped as-is |

### Content Mapping

| Entire.io Section | Vault Section | Transformation |
|-------------------|---------------|-----------------|
| session.decisions[*] | Key Decisions | Create wiki-links to vault decisions |
| session.context.shifts[*] | Context Shifts | Direct copy, one per line |
| session.lessons[*] | Extracted Learnings | Create wiki-links with severity |
| session.outcomes[*].artifacts | Session Artifacts | Create wiki-links if in vault |
| session.outcomes[*].summary | Execution Summary | Include in status line |
| (inferred) | Related Research | Cross-reference SurrealDB papers |

---

## Transformation Rules

### 1. Frontmatter Generation

```python
# Pseudo-code for daemon

frontmatter = {
    "date": session["start_timestamp"],  # ISO format
    "title": f"Agent Execution Summary - {session['id']}",
    "tags": ["agent", "execution", "entire.io"],
    "status": "archived",  # Always archived
    "source": "entire.io",  # Always this source
    "session_id": session["id"],
    "agent_names": [agent["name"] for agent in session["agents"]]
}
```

### 2. Execution Summary Generation

```python
# Extract metrics from session
duration_ms = session["duration_ms"]
status = session["status"]
model = session["agents"][0]["model"]  # Primary model
total_turns = sum(a["turns"] for a in session["agents"])
total_functions = sum(a["functions"] for a in session["agents"])

execution_summary = f"""## Execution Summary

**Duration**: {duration_ms}ms
**Status**: {status}
**Model**: {model}
**Turns**: {total_turns}
**Functions**: {total_functions}
"""
```

### 3. Key Decisions Mapping

```python
# Convert entire.io decisions to vault wiki-links

key_decisions = ""
for decision in session["decisions"]:
    # Look up decision in vault, or create if missing
    decision_title = decision["title"]
    decision_path = vault.find_decision_or_create(decision_title)
    key_decisions += f"- [[{decision_path}]] - {decision['reasoning']}\n"
```

**Rules**:
- Try to link to existing `decisions/` note
- If not found, create new decision note with decision body
- Link with reasoning as description
- No formatting of title needed (done by [[]])

### 4. Context Shifts

```python
# Direct copy from entire.io context.shifts

context_shifts = ""
for shift in session["context"]["shifts"]:
    context_shifts += f"- {shift}\n"
```

**Rules**:
- Copy verbatim from entire.io
- No markdown formatting
- One shift per line

### 5. Extracted Learnings Mapping

```python
# Convert entire.io lessons to vault wiki-links

extracted_learnings = ""
for lesson in session["lessons"]:
    lesson_title = lesson["title"]
    lesson_path = vault.find_lesson_or_create(lesson_title)
    auto_tag = " (auto-extracted)" if lesson["auto_extracted"] else ""
    extracted_learnings += f"- [[{lesson_path}]] - Severity: {lesson['severity']}{auto_tag}\n"
```

**Rules**:
- Try to link to existing `lessons/` note
- If not found, create new lesson note
- Include severity from entire.io
- Add "(auto-extracted)" tag for system-identified lessons

### 6. Session Artifacts Mapping

```python
# Convert entire.io artifacts to vault wiki-links if they exist

session_artifacts = ""
for artifact in session["outcomes"]["artifacts"]:
    # Check if artifact path exists in vault
    if vault.note_exists(artifact):
        session_artifacts += f"- [[{artifact}]]\n"
    else:
        # Skip if not in vault (external files, temp outputs)
        logger.debug(f"Artifact {artifact} not in vault, skipping")
```

**Rules**:
- Only link to vault notes that exist
- Skip external files, temp outputs, API responses
- Common artifacts: decisions, patterns, experiments, analysis files

### 7. Related Research Mapping

```python
# Cross-reference SurrealDB to find papers related to session

related_papers = []
# Option 1: Use SurrealDB query
#   SELECT paper FROM session->relates_to_paper->paper
# Option 2: Infer from decision -> derives_from_research
#   SELECT paper FROM decisions->derives_from_research->paper

related_research = ""
for paper in related_papers:
    paper_title = vault.get_paper_title(paper)
    related_research += f"- [[sensory/{paper}]] - Research reference\n"
```

**Rules**:
- Query SurrealDB for session->relates_to_paper edges
- Include papers that informed decisions
- Link format: `[[sensory/title-slug]]`
- Include context if available (from SurrealDB edge properties)

### 8. Metrics & Performance

```python
# Copy metrics directly from entire.io

metrics_json = json.dumps(session["metrics"], indent=2)
metrics_section = f"""## Metrics & Performance

{metrics_json}
"""
```

**Rules**:
- Copy entire metrics object as-is
- Ensure valid JSON formatting
- Include all fields from entire.io
- Add computed fields: hours_actual, variance_percent, etc.

### 9. Session ID Footer

```python
footer = f"""## Session ID

`{session["id"]}`
"""
```

**Rules**:
- Always include for SurrealDB linkage
- Use code block formatting (backticks)
- Exactly as provided by entire.io

---

## Error Handling & Edge Cases

### Missing Fields in Entire.io Response

| Field | Fallback |
|-------|----------|
| session.decisions | Skip "Key Decisions" section |
| session.context.shifts | Skip "Context Shifts" section |
| session.lessons | Skip "Extracted Learnings" section |
| session.outcomes[*].artifacts | Skip "Session Artifacts" section |
| session.metrics.* | Use 0 or "unknown" |

### Decision/Lesson Not in Vault

**Option A: Create new note** (recommended)
```python
if not vault.exists(decision_title):
    vault.create_decision(
        title=decision_title,
        context=f"Created from agent session {session_id}",
        decision=decision_body,
        consequences="To be reviewed in retrospective",
        alternatives=decision["alternatives"]
    )
```

**Option B: Skip link** (conservative)
```python
# Just record the title, don't create note
key_decisions += f"- {decision_title} - {decision['reasoning']}\n"
```

**Recommendation**: Option A (create new notes) enables better cross-referencing

### Special Characters in Fields

```python
# Escape markdown special characters
def escape_markdown(text):
    # Escape [ ] when not part of wiki-links
    # Preserve [[]] for wiki-links
    pass

# Use YAML-safe representation in frontmatter
yaml.safe_dump(data)
```

### Non-ISO Timestamps

```python
# Ensure entire.io returns ISO 8601
# Fallback: parse and re-format
from datetime import datetime
if not timestamp.endswith('Z'):
    timestamp = datetime.fromisoformat(timestamp).isoformat() + 'Z'
```

---

## Implementation Checklist for Daemon (Week 2)

- [ ] Parse entire.io API response (JSON structure above)
- [ ] Extract session metadata (id, dates, agents, status)
- [ ] Calculate aggregate metrics (total_turns, total_functions)
- [ ] Generate frontmatter (8 required fields)
- [ ] Generate Execution Summary section
- [ ] Link to decisions in vault
- [ ] Copy context shifts verbatim
- [ ] Link to lessons in vault
- [ ] Link to artifacts in vault
- [ ] Query SurrealDB for related papers
- [ ] Generate metrics JSON section
- [ ] Include session ID footer
- [ ] Write to `daily/agent-logs/YYYY-MM-DDTHH-MM-ss-{session_id}.md`
- [ ] Validate frontmatter YAML
- [ ] Validate wiki-links resolve
- [ ] Test error handling
- [ ] Add to git (no .gitignore needed)

---

## Example Transformation

### Entire.io Input
```json
{
  "session": {
    "id": "sess-phase1-step1",
    "start_timestamp": "2026-02-11T14:30:00Z",
    "end_timestamp": "2026-02-11T14:45:22Z",
    "duration_ms": 914000,
    "status": "completed",
    "agents": [
      {"name": "vault-architect", "model": "haiku", "turns": 12, "functions": 24}
    ],
    "metrics": {"total_turns": 12, "total_functions": 24, "errors": 0, "recovery_attempts": 0},
    "context": {"shifts": ["Task: Schema → Task: Integration"]},
    "decisions": [
      {"title": "Use SurrealDB for agent context", "reasoning": "Native graph", "alternatives": ["PostgreSQL"], "chosen": "SurrealDB"}
    ],
    "lessons": [
      {"title": "Implementation-first works", "severity": "CRITICAL", "auto_extracted": true}
    ]
  }
}
```

### Vault Output
```markdown
---
date: "2026-02-11T14:30:00Z"
title: "Agent Execution Summary - sess-phase1-step1"
tags: [agent, execution, entire.io]
status: archived
source: entire.io
session_id: "sess-phase1-step1"
agent_names: [vault-architect]
---

## Execution Summary

**Duration**: 914000ms
**Status**: completed
**Model**: haiku
**Turns**: 12
**Functions**: 24

## Key Decisions

- [[surrealdb]] - Native graph edges

## Context Shifts

- Task: Schema → Task: Integration

## Extracted Learnings

- [[implementation-first-infrastructure-later]] - Severity: CRITICAL (auto-extracted)

## Metrics & Performance

{
  "total_turns": 12,
  "total_functions": 24,
  "errors": 0,
  "recovery_attempts": 0
}

## Session ID

`sess-phase1-step1`
```

---

## Related Documentation

- `daily/agent-logs/_template.md` - Template for daemon output
- `patterns/agent-logs-vault-schema.md` - Schema reference
- `PHASE_1_AGENT_CONTEXT_INTEGRATION.md` - Week 2 daemon spec

---

**Last Updated**: 2026-02-11
**Status**: Ready for daemon implementation
**Next Review**: 2026-02-13 (after Phase 1 testing)

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-09-fastmcp-asgi-integration-fix]]
- [[2026-02-14-graphrag-verification-and-integration-session]]
- [[automated-concept-extraction]]
- [[sheetsbr idge-mcp-testing]]
- [[phase1-production-validation-runbook]]
- [[typescript-error-diagnostic]]
- [[surrealdb-query-driven-analysis]]
