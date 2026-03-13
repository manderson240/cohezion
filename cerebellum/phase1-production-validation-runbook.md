---
title: "Phase 1 Production Validation Runbook"
date: 2026-02-11
status: proposed
tags: [pattern, runbook, phase1, production-validation, surrealdb, agent-context]
aspect: thinker
neural:
  activation: 0.92
  stage: growing
  synapse_in: 24
  synapse_out: 9
---

# Phase 1 Production Validation Runbook

Comprehensive validation procedure for Phase 1 SurrealDB Agent Context Schema before production sign-off.

## Pre-Validation Checklist

- [ ] All Phase 1 Steps 1-5 marked complete
- [ ] SurrealDB instance running at http://localhost:8000
- [ ] Cloud Vault MCP server available at port 8360
- [ ] All integration tests passing (43/43)
- [ ] Documentation complete and reviewed

## Validation Procedure (60 minutes)

### Phase 1A: Schema Validation (10 minutes)

#### 1.1 Verify all tables exist
```bash
# Connect to SurrealDB
curl -u root:root http://localhost:8000/sql -X POST \
  -H "NS: cohezion" \
  -H "DB: vault" \
  -d "INFO FOR DB;" | jq '.result[0].tb' | grep -E "(agent_session|agent_decision|agent_outcome|agent_reasoning|agent_context)"
```

**Expected**: 5 table definitions returned
- [ ] agent_session
- [ ] agent_decision
- [ ] agent_outcome
- [ ] agent_reasoning (Phase 2, may be absent)
- [ ] agent_context (Phase 3, may be absent)

#### 1.2 Verify all indexes exist
```bash
# Check indexes
curl -u root:root http://localhost:8000/sql -X POST \
  -H "NS: cohezion" \
  -H "DB: vault" \
  -d "SELECT * FROM information_schema.INDEXES WHERE table_name LIKE 'agent_%';" | jq '.result[0]'
```

**Expected**: At least 3 indexes
- [ ] idx_decision_session
- [ ] idx_decision_timestamp
- [ ] idx_outcome_session

#### 1.3 Verify relationship tables exist
```bash
# Check edges
curl -u root:root http://localhost:8000/sql -X POST \
  -H "NS: cohezion" \
  -H "DB: vault" \
  -d "INFO FOR DB;" | jq '.result[0].tb' | grep -E "(applied_research|validates_lesson)"
```

**Expected**: Relationship tables
- [ ] applied_research or edge type for APPLIED_RESEARCH
- [ ] validates_lesson or edge type for VALIDATES_LESSON

### Phase 1B: Tool Integration Validation (15 minutes)

#### 1.4 Verify MCP tools registered
```bash
# Test that tools are accessible in MCP server
# (requires running MCP server and testing via Claude)
python3 -c "
from mcp_server.server import create_server
from mcp_server.config import ServerConfig
import os

os.environ['VAULT_PATH'] = '/home/mike-anderson/vaults/cohezion-vault'
os.environ['SURREALDB_ENABLED'] = 'true'
os.environ['SURREALDB_URL'] = 'http://localhost:8000'

config = ServerConfig.from_env()
mcp = create_server(config)

# Check tools exist
tools = [name for name in dir(mcp) if not name.startswith('_')]
print('Tools registered:', len(tools))
"
```

**Expected**: 3+ tools available
- [ ] track_session
- [ ] record_decision
- [ ] record_outcome

#### 1.5 Test track_session tool
```bash
# Create test session
curl -X POST http://localhost:8360/tools/track_session \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "validation-test",
    "goals": ["validate-phase1"],
    "model_used": "claude-haiku-4-5",
    "phase": "validation"
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "session_id": "agent_session:...",
  "agent_id": "validation-test",
  "status": "in_progress",
  "timestamp": "2026-02-11T..."
}
```

**Validation Points**:
- [ ] success = true
- [ ] session_id returned
- [ ] status = "in_progress"
- [ ] timestamp is valid ISO format

#### 1.6 Test record_decision tool
```bash
# Create test decision with sample papers
# (assumes papers exist in SurrealDB)
curl -X POST http://localhost:8360/tools/record_decision \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<from_1.5>",
    "decision_type": "architecture",
    "reasoning": "Test decision for validation",
    "papers_applied": ["paper:p1", "paper:p2"],
    "confidence_score": 0.85
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "decision_id": "agent_decision:...",
  "links_created": 2,
  "total_papers": 2,
  "confidence_score": 0.85
}
```

**Validation Points**:
- [ ] success = true
- [ ] decision_id returned
- [ ] links_created = 2 (both papers linked)
- [ ] confidence_score preserved

#### 1.7 Test record_outcome tool
```bash
# Record outcome for validation
curl -X POST http://localhost:8360/tools/record_outcome \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<from_1.5>",
    "outcome_type": "success",
    "lessons_learned": ["lesson:l1", "lesson:l2"],
    "metrics": {
      "session_duration_min": 15,
      "token_efficiency_ratio": 2.5,
      "decisions_made": 1,
      "decisions_validated": 1
    }
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "outcome_id": "agent_outcome:...",
  "validated_lessons": 2,
  "outcome_type": "success"
}
```

**Validation Points**:
- [ ] success = true
- [ ] outcome_id returned
- [ ] validated_lessons = 2
- [ ] outcome_type preserved

### Phase 1C: Query Validation (20 minutes)

#### 1.8 Research Lineage Query
```bash
# Execute research lineage query
curl -u root:root http://localhost:8000/sql -X POST \
  -H "NS: cohezion" \
  -H "DB: vault" \
  -d "
    SELECT
      agent_decision.{id, decision_type, reasoning, confidence_score},
      ->applied_research->paper.{title, date},
      ->applied_research.relevance_score
    FROM agent_decision
    WHERE id = '<decision_id_from_1.6>'
    LIMIT 10
  " | jq '.result[0]'
```

**Expected**: Research lineage showing papers linked to decision
- [ ] decision_id present
- [ ] decision_type = "architecture"
- [ ] papers linked (array of paper nodes)
- [ ] relevance_score on edges (0.8)

**Validation Points**:
- [ ] Query returns results (no errors)
- [ ] Papers are linked correctly
- [ ] Edge properties populated

#### 1.9 Lesson Validation Query
```bash
# Execute lesson validation query
curl -u root:root http://localhost:8000/sql -X POST \
  -H "NS: cohezion" \
  -H "DB: vault" \
  -d "
    SELECT
      agent_outcome.{id, outcome_type, metrics},
      ->validates_lesson->lesson.{title, severity},
      ->validates_lesson.alignment_score
    FROM agent_outcome
    WHERE id = '<outcome_id_from_1.7>'
  " | jq '.result[0]'
```

**Expected**: Lesson validation showing lessons linked to outcome
- [ ] outcome_id present
- [ ] outcome_type = "success"
- [ ] lessons linked (array of lesson nodes)
- [ ] alignment_score on edges (0.85)

**Validation Points**:
- [ ] Query returns results (no errors)
- [ ] Lessons are linked correctly
- [ ] Edge properties populated
- [ ] Metrics aggregated correctly

#### 1.10 Decision Cascade Query
```bash
# Execute cascading decision query
curl -u root:root http://localhost:8000/sql -X POST \
  -H "NS: cohezion" \
  -H "DB: vault" \
  -d "
    SELECT
      agent_decision.{id, decision_type, timestamp},
      <-relates_to_decision<-agent_decision.{id, decision_type},
      ->relates_to_decision->agent_decision.{id, decision_type}
    FROM agent_decision
    WHERE session_id = '<session_id_from_1.5>'
    ORDER BY timestamp ASC
  " | jq '.result[0]'
```

**Expected**: Decision cascade structure (may be empty if only 1 decision)
- [ ] Query executes without errors
- [ ] Returns decision cascade or empty set (valid)

**Validation Points**:
- [ ] Query syntax correct
- [ ] Handles empty results gracefully

#### 1.11 Metrics Query
```bash
# Aggregate metrics across outcomes
curl -u root:root http://localhost:8000/sql -X POST \
  -H "NS: cohezion" \
  -H "DB: vault" \
  -d "
    SELECT
      id,
      outcome_type,
      metrics.session_duration_min,
      metrics.token_efficiency_ratio,
      metrics.decisions_made
    FROM agent_outcome
    WHERE session_id = '<session_id_from_1.5>'
  " | jq '.result[0]'
```

**Expected**: Metrics properly aggregated
- [ ] session_duration_min = 15
- [ ] token_efficiency_ratio = 2.5
- [ ] decisions_made = 1

**Validation Points**:
- [ ] Metrics extracted correctly from JSON objects
- [ ] Data types preserved (numbers not strings)

### Phase 1D: Test Coverage Validation (10 minutes)

#### 1.12 Verify unit test pass rate
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp && \
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 \
  -m pytest tests/test_agent_context.py -v --tb=short
```

**Expected**: 11/11 tests passing
- [ ] test_track_session_success
- [ ] test_track_session_failure
- [ ] test_track_session_exception
- [ ] test_record_decision_success
- [ ] test_record_decision_missing_session
- [ ] test_record_decision_partial_paper_links
- [ ] test_record_outcome_success
- [ ] test_record_outcome_missing_session
- [ ] test_record_outcome_partial_lessons
- [ ] test_record_outcome_exception
- [ ] test_full_workflow

#### 1.13 Verify integration test pass rate
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp && \
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 \
  -m pytest tests/test_agent_context_integration.py -v --tb=short
```

**Expected**: 13/13 tests passing
- [ ] Happy path workflow
- [ ] Partial failures handling
- [ ] Invalid session errors
- [ ] Decision/outcome creation failures
- [ ] Research lineage structure
- [ ] Lesson validation structure
- [ ] Metrics aggregation
- [ ] Edge integrity (papers)
- [ ] Edge integrity (lessons)
- [ ] Session completion cascade
- [ ] Token updates
- [ ] Metadata preservation
- [ ] Decision metadata preservation

#### 1.14 Check code coverage
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp && \
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3 \
  -m pytest tests/test_agent_context*.py --cov=src/mcp_server/agent_context --cov-report=term-missing
```

**Expected**: ≥85% coverage
- [ ] agent_context.py: ≥85%

### Phase 1E: Documentation Validation (5 minutes)

#### 1.15 Verify tool documentation
- [ ] MCP Tool Reference exists and is complete
- [ ] All 3 tools documented (track_session, record_decision, record_outcome)
- [ ] Examples provided for each tool
- [ ] Return values documented
- [ ] Error cases documented

#### 1.16 Verify query templates
- [ ] Research lineage query template provided
- [ ] Lesson validation query template provided
- [ ] Decision cascade query template provided
- [ ] Metrics aggregation query template provided
- [ ] Common filtering patterns documented

#### 1.17 Verify troubleshooting guide
- [ ] Missing APPLIED_RESEARCH edges troubleshooting
- [ ] Lesson alignment scores explanation
- [ ] Performance tips documented
- [ ] Common errors and solutions

## Sign-Off Criteria

### All Criteria Must Be Met for Production Sign-Off

#### ✅ Schema Validation (1.1-1.3)
- [ ] All 5 tables exist
- [ ] All indexes created
- [ ] Relationship types defined

#### ✅ Tool Integration (1.4-1.7)
- [ ] All 3 tools registered in MCP
- [ ] track_session creates nodes correctly
- [ ] record_decision creates edges correctly
- [ ] record_outcome creates edges correctly

#### ✅ Query Validation (1.8-1.11)
- [ ] Research lineage queries execute successfully
- [ ] Lesson validation queries execute successfully
- [ ] Decision cascade queries execute successfully
- [ ] Metrics queries return correct data

#### ✅ Test Coverage (1.12-1.14)
- [ ] 100% unit test pass rate (11/11)
- [ ] 100% integration test pass rate (13/13)
- [ ] ≥85% code coverage

#### ✅ Documentation (1.15-1.17)
- [ ] Tool documentation complete
- [ ] Query templates provided
- [ ] Troubleshooting guide complete

#### ✅ No Regressions
- [ ] No breaking changes to existing tools
- [ ] All existing tests still pass
- [ ] No new warnings or errors introduced

## Post-Validation Steps

### If All Criteria Met ✅
1. Mark Phase 1 complete
2. Archive validation results
3. Update deployment checklist
4. Proceed to Phase 2 planning
5. Begin Week 1 Entire.io daemon implementation

### If Any Criteria Fail ⚠️
1. Document failing criteria
2. Identify root cause
3. Create fix + regression test
4. Re-run affected validation steps
5. Return to sign-off criteria review

## Related

**Patterns**: [[2026-02-11-phase-1-agent-context-schema-complete]], [[error-handling-with-dlq]]

**Decisions**: [[2026-02-11-phase-1-agent-context-schema-complete]]

**Projects**: [[2026-02-11-phase-1-agent-context-schema-complete]]

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-14-phase-6b-cascade-impact-computation]]
- [[2026-02-11-phase-1-agent-context-schema-complete]]
- [[2026-02-14-track-a-sign-off-approved]]
- [[2026-02-13-phase-2-track-a-complete]]
- [[2026-02-14-phase-6c-semantic-contradiction-detection-complete]]
- [[2026-02-11-phase1-completion-summary]]
- [[2026-02-11-phase1-execution-status]]
