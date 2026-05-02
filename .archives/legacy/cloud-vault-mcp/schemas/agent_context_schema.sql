-- ============================================================================
-- Agent Context Schema for Entire.io Integration
-- ============================================================================
-- Purpose: Track agent decision-making, reasoning chains, outcomes, and lessons
-- Nodes: 5 (session, agent_decision, agent_action, agent_outcome, lesson_validation)
-- Edges: 8 (decision→action, action→outcome, outcome→lesson, etc.)
-- ============================================================================

USE NS cohezion;
USE DB vault;

-- ============================================================================
-- TABLE 1: agent_session (root context node)
-- ============================================================================
-- Represents a discrete agent execution context (decision-making session)
-- One session = one decision → multiple actions → one outcome

CREATE TABLE IF NOT EXISTS agent_session SCHEMALESS;

-- Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_agent_session_id ON TABLE agent_session FIELDS id;
CREATE INDEX IF NOT EXISTS idx_agent_session_agent ON TABLE agent_session FIELDS agent_name;
CREATE INDEX IF NOT EXISTS idx_agent_session_date ON TABLE agent_session FIELDS started_at;
CREATE INDEX IF NOT EXISTS idx_agent_session_status ON TABLE agent_session FIELDS status;
CREATE INDEX IF NOT EXISTS idx_agent_session_decision ON TABLE agent_session FIELDS decision_id;

-- ============================================================================
-- TABLE 2: agent_decision (core decision node)
-- ============================================================================
-- Represents a single decision point: "What approach to take?"
-- Each session produces exactly one decision

CREATE TABLE IF NOT EXISTS agent_decision SCHEMALESS;

-- Create indexes for research lineage
CREATE INDEX IF NOT EXISTS idx_agent_decision_id ON TABLE agent_decision FIELDS id;
CREATE INDEX IF NOT EXISTS idx_agent_decision_session ON TABLE agent_decision FIELDS session_id;
CREATE INDEX IF NOT EXISTS idx_agent_decision_vault_ref ON TABLE agent_decision FIELDS vault_decision_file;
CREATE INDEX IF NOT EXISTS idx_agent_decision_tags ON TABLE agent_decision FIELDS tags;
CREATE INDEX IF NOT EXISTS idx_agent_decision_reasoning ON TABLE agent_decision FIELDS reasoning_confidence;

-- ============================================================================
-- TABLE 3: agent_action (execution node)
-- ============================================================================
-- Represents a concrete action: tool call, decision step, or resource operation
-- One decision → many actions (sequential or parallel)

CREATE TABLE IF NOT EXISTS agent_action SCHEMALESS;

-- Create indexes for execution pattern analysis
CREATE INDEX IF NOT EXISTS idx_agent_action_id ON TABLE agent_action FIELDS id;
CREATE INDEX IF NOT EXISTS idx_agent_action_decision ON TABLE agent_action FIELDS decision_id;
CREATE INDEX IF NOT EXISTS idx_agent_action_tool ON TABLE agent_action FIELDS tool_name;
CREATE INDEX IF NOT EXISTS idx_agent_action_sequence ON TABLE agent_action FIELDS sequence_order;
CREATE INDEX IF NOT EXISTS idx_agent_action_timestamp ON TABLE agent_action FIELDS executed_at;

-- ============================================================================
-- TABLE 4: agent_outcome (result node)
-- ============================================================================
-- Represents the final outcome of a decision: success, error, partial, etc.
-- Includes cost, token usage, execution time

CREATE TABLE IF NOT EXISTS agent_outcome SCHEMALESS;

-- Create indexes for cost/performance analysis
CREATE INDEX IF NOT EXISTS idx_agent_outcome_id ON TABLE agent_outcome FIELDS id;
CREATE INDEX IF NOT EXISTS idx_agent_outcome_decision ON TABLE agent_outcome FIELDS decision_id;
CREATE INDEX IF NOT EXISTS idx_agent_outcome_status ON TABLE agent_outcome FIELDS outcome_status;
CREATE INDEX IF NOT EXISTS idx_agent_outcome_cost ON TABLE agent_outcome FIELDS actual_cost;
CREATE INDEX IF NOT EXISTS idx_agent_outcome_efficiency ON TABLE agent_outcome FIELDS cost_per_lesson;

-- ============================================================================
-- TABLE 5: lesson_validation (lesson linkage node)
-- ============================================================================
-- Connects agent outcomes to lessons learned in the vault
-- Enables queries: "Which agent work generated this lesson?"

CREATE TABLE IF NOT EXISTS lesson_validation SCHEMALESS;

-- Create indexes for lesson traceability
CREATE INDEX IF NOT EXISTS idx_lesson_validation_id ON TABLE lesson_validation FIELDS id;
CREATE INDEX IF NOT EXISTS idx_lesson_validation_outcome ON TABLE lesson_validation FIELDS outcome_id;
CREATE INDEX IF NOT EXISTS idx_lesson_validation_lesson ON TABLE lesson_validation FIELDS lesson_vault_file;
CREATE INDEX IF NOT EXISTS idx_lesson_validation_confidence ON TABLE lesson_validation FIELDS confidence_score;

-- ============================================================================
-- EDGE TABLES (Relationships)
-- ============================================================================

-- EDGE 1: session → decision
CREATE TABLE IF NOT EXISTS session_decision SCHEMALESS;
CREATE INDEX IF NOT EXISTS idx_session_decision_src ON TABLE session_decision FIELDS in;
CREATE INDEX IF NOT EXISTS idx_session_decision_dst ON TABLE session_decision FIELDS out;

-- EDGE 2: decision → action
CREATE TABLE IF NOT EXISTS decision_action SCHEMALESS;
CREATE INDEX IF NOT EXISTS idx_decision_action_src ON TABLE decision_action FIELDS in;
CREATE INDEX IF NOT EXISTS idx_decision_action_dst ON TABLE decision_action FIELDS out;

-- EDGE 3: action → outcome
CREATE TABLE IF NOT EXISTS action_outcome SCHEMALESS;
CREATE INDEX IF NOT EXISTS idx_action_outcome_src ON TABLE action_outcome FIELDS in;
CREATE INDEX IF NOT EXISTS idx_action_outcome_dst ON TABLE action_outcome FIELDS out;

-- EDGE 4: outcome → lesson
CREATE TABLE IF NOT EXISTS outcome_lesson SCHEMALESS;
CREATE INDEX IF NOT EXISTS idx_outcome_lesson_src ON TABLE outcome_lesson FIELDS in;
CREATE INDEX IF NOT EXISTS idx_outcome_lesson_dst ON TABLE outcome_lesson FIELDS out;

-- EDGE 5: decision → vault_decision (backlink to vault)
CREATE TABLE IF NOT EXISTS decision_vault_ref SCHEMALESS;
CREATE INDEX IF NOT EXISTS idx_decision_vault_src ON TABLE decision_vault_ref FIELDS in;
CREATE INDEX IF NOT EXISTS idx_decision_vault_dst ON TABLE decision_vault_ref FIELDS out;

-- EDGE 6: outcome → vault_experiment (backlink to experiment)
CREATE TABLE IF NOT EXISTS outcome_vault_ref SCHEMALESS;
CREATE INDEX IF NOT EXISTS idx_outcome_vault_src ON TABLE outcome_vault_ref FIELDS in;
CREATE INDEX IF NOT EXISTS idx_outcome_vault_dst ON TABLE outcome_vault_ref FIELDS out;

-- EDGE 7: lesson → decision (cascade detection)
CREATE TABLE IF NOT EXISTS lesson_decision_cascade SCHEMALESS;
CREATE INDEX IF NOT EXISTS idx_cascade_lesson ON TABLE lesson_decision_cascade FIELDS in;
CREATE INDEX IF NOT EXISTS idx_cascade_decision ON TABLE lesson_decision_cascade FIELDS out;

-- EDGE 8: error_pattern (for lesson extraction)
CREATE TABLE IF NOT EXISTS error_pattern_edge SCHEMALESS;
CREATE INDEX IF NOT EXISTS idx_error_pattern_outcome ON TABLE error_pattern_edge FIELDS in;
CREATE INDEX IF NOT EXISTS idx_error_pattern_lesson ON TABLE error_pattern_edge FIELDS out;

-- ============================================================================
-- SCHEMA REFERENCE (Data Structure for Each Table)
-- ============================================================================

/*

TABLE: agent_session
---
FIELDS:
  id (string, PK):           "session:UUID-or-timestamp"
  agent_name (string):       "observability-specialist", "integration-engineer", etc.
  started_at (datetime):     ISO 8601 timestamp
  ended_at (datetime?):      ISO 8601 timestamp (null if in-progress)
  status (string):           "in-progress", "success", "error", "partial"
  decision_id (string):      Reference to agent_decision
  context (object):          {"model": "Haiku 4.5", "temperature": 0.7, ...}
  metadata (object):         Custom metadata from entire.io or agent

---

TABLE: agent_decision
---
FIELDS:
  id (string, PK):           "decision:UUID"
  session_id (string):       Reference to agent_session
  vault_decision_file (string?): Path to vault decision file (backlink)
  title (string):            "Use Ollama embeddings vs API"
  problem_statement (string): "What approach to optimize cost?"
  chosen_option (string):    "Ollama embeddings"
  alternatives (array):      ["OpenAI API", "Anthropic API"]
  decision_reasoning (object):
    - rationale (string):    "Cost $0 vs $15, local control, latency <100ms"
    - confidence (float):    0.95
    - reasoning_chain (array): Steps in the reasoning process
  estimated_cost (float):    2.00
  estimated_time_hours (float): 4.5
  created_at (datetime):     ISO 8601
  decision_category (string): "cost-optimization", "risk-mitigation", etc.
  tags (array):              ["cost", "performance", "infrastructure"]

---

TABLE: agent_action
---
FIELDS:
  id (string, PK):           "action:UUID"
  decision_id (string):      Reference to agent_decision
  sequence_order (int):      1, 2, 3... (order in execution)
  tool_name (string):        "Bash", "Read", "Grep", "Bash:git-gc", etc.
  tool_input (object):       Parameters passed to tool
  executed_at (datetime):    ISO 8601
  completed_at (datetime):   ISO 8601
  execution_time_ms (int):   Latency in milliseconds
  status (string):           "success", "error", "retry", "skipped"
  result_summary (string):   Truncated result (first 500 chars)
  tokens_used (int?):        Token count if applicable
  cost_usd (float?):         Cost for this action if applicable

---

TABLE: agent_outcome
---
FIELDS:
  id (string, PK):           "outcome:UUID"
  decision_id (string):      Reference to agent_decision
  session_id (string):       Reference to agent_session
  vault_experiment_file (string?): Path to vault experiment file
  outcome_status (string):   "success", "partial", "failed", "aborted"
  summary (string):          "Decision executed successfully"
  actions_count (int):       Total number of actions
  actual_cost (float):       Actual cost in USD
  estimated_cost (float):    Original estimate
  cost_delta_pct (float):    Percentage difference
  total_time_seconds (int):  End-to-end execution time
  total_tokens (int?):       Total tokens consumed
  cost_per_lesson (float?):  Cost divided by lessons generated
  error_description (string?): If outcome_status != "success"
  root_cause (string?):      "training data committed to git", etc.
  resolution_applied (string?): How the error was fixed
  lessons_generated (array?): ["lesson-data-discipline", ...]
  completed_at (datetime):   ISO 8601
  vault_note_generated (boolean): Whether experiment/decision was recorded in vault

---

TABLE: lesson_validation
---
FIELDS:
  id (string, PK):           "lesson_val:UUID"
  outcome_id (string):       Reference to agent_outcome
  lesson_vault_file (string): Path to lesson in vault
  lesson_title (string):     "Data Discipline: Prevent Generated Data in Git"
  triggered_by_error (boolean): true if outcome was error
  confidence_score (float):  0.0-1.0 (how certain is this lesson?)
  decision_error_chain (object): {
    "error_class": "git-repo-bloat",
    "root_cause": "Training data committed to git (418 files, 78K lines)",
    "impact": "12 GB wasted, broke CI/CD",
    "detection_window_minutes": 1440,
    "cost_to_recover": 3
  }
  applicability (object): {
    "scope": "All ML/data projects in cohezion",
    "exceptions": "Small static datasets <1MB"
  }
  preventions (array): ["Pre-commit hook", "Data governance pattern #3"]
  created_at (datetime):     ISO 8601
  linked_decisions (array?): Other decisions that could have triggered this

*/

-- ============================================================================
-- STRATEGIC QUERIES (To be implemented in MCP tools)
-- ============================================================================

/*

QUERY 1: Research Lineage (Papers → Decisions → Lessons)
SELECT
  p.title as paper_title,
  p.path as paper_path,
  d.title as decision_title,
  d.chosen_option,
  d.decision_reasoning,
  o.outcome_status,
  lv.lesson_title,
  lv.confidence_score
FROM paper as p
  -> concept_link -> concept as c
  -> decision_link -> agent_decision as d
  -> decision_action -> agent_action as a
  -> action_outcome -> agent_outcome as o
  -> outcome_lesson -> lesson_validation as lv
WHERE p.path LIKE '%papers%'
ORDER BY p.created_at DESC, d.created_at DESC;

QUERY 2: Lesson Validation (Outcomes that generated lessons)
SELECT
  ao.outcome_status,
  COUNT(lv.id) as lessons_generated,
  SUM(ao.actual_cost) as total_cost,
  AVG(lv.confidence_score) as avg_confidence,
  GROUP_CONCAT(lv.lesson_title) as lesson_titles
FROM agent_outcome as ao
  -> outcome_lesson -> lesson_validation as lv
GROUP BY ao.id
ORDER BY lessons_generated DESC;

QUERY 3: Cascade Detection (Lessons preventing future errors)
SELECT
  lv.lesson_title,
  COUNT(ldc.out) as future_decisions_affected,
  ldc.out.outcome_status as future_outcome
FROM lesson_validation as lv
  <- outcome_lesson <- agent_outcome as ao
  -> outcome_lesson -> lesson_validation as lv2
  <- lesson_decision_cascade -> agent_decision as ldc
WHERE lv.triggered_by_error = true
  AND ldc.created_at > lv.created_at
ORDER BY future_decisions_affected DESC;

*/

-- ============================================================================
-- INITIALIZATION (Sample insert for reference)
-- ============================================================================

/*
Example: Insert a complete session → decision → action → outcome → lesson flow

-- 1. Create session
UPSERT agent_session:`session:2026-02-11-001` SET
  agent_name = 'observability-specialist',
  started_at = fn::now(),
  status = 'in-progress',
  context = {
    model: 'Haiku 4.5',
    temperature: 0.7,
    max_tokens: 4000
  };

-- 2. Create decision
UPSERT agent_decision:`decision:2026-02-11-001` SET
  session_id = 'session:2026-02-11-001',
  title = 'SurrealDB Schema for Agent Context',
  chosen_option = 'Design 5-node graph with decision→action→outcome chain',
  decision_reasoning = {
    rationale: 'Captures full decision lifecycle + cost metrics + lesson linkage',
    confidence: 0.95,
    alternatives: ['Flat log table', 'NoSQL document store']
  },
  estimated_cost = 0.0,
  estimated_time_hours = 2.0,
  created_at = fn::now(),
  tags = ['schema-design', 'observability', 'graph-db'];

-- 3-4. Create action + outcome (abbreviated)
-- (see full template in tests)

-- 5. Link to vault decision
UPSERT decision_vault_ref:`dv:ref:001` SET
  in = 'agent_decision:`decision:2026-02-11-001`',
  out = 'vault_decision:decisions/2026-02-11-vault-first-knowledge-architecture',
  created_at = fn::now();

*/

-- ============================================================================
-- End of Schema
-- ============================================================================
