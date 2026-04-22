-- ───────────────────────────────────────────────────────────────────────────────
-- Agent Context Schema Phase 2: Agent Reasoning + Decision Cascades
-- Extends Phase 1 with: agent_reasoning nodes + challenge/cascade edges
-- ───────────────────────────────────────────────────────────────────────────────

-- ═══════════════════════════════════════════════════════════════════════════════
-- PHASE 2: NEW TABLES & NODE TYPES
-- ═══════════════════════════════════════════════════════════════════════════════

-- agent_reasoning: Captures WHY a decision was made
-- Reasoning types: research (papers), pattern (known patterns), intuition (agent judgment),
--                  convention (team standards), hybrid (combination)
CREATE TABLE IF NOT EXISTS agent_reasoning SCHEMALESS;

DEFINE FIELD id ON TABLE agent_reasoning TYPE string;
DEFINE FIELD decision_id ON TABLE agent_reasoning TYPE string;  -- Links to decision
DEFINE FIELD reasoning_type ON TABLE agent_reasoning TYPE string;  -- research|pattern|intuition|convention|hybrid
DEFINE FIELD reasoning_chain ON TABLE agent_reasoning TYPE array;  -- Step-by-step chain of thought
DEFINE FIELD confidence_score ON TABLE agent_reasoning TYPE number;  -- 0.0-1.0
DEFINE FIELD assumptions ON TABLE agent_reasoning TYPE array;  -- What was assumed to be true
DEFINE FIELD alternatives_rejected ON TABLE agent_reasoning TYPE array;  -- [{option, reason}, ...]
DEFINE FIELD created_at ON TABLE agent_reasoning TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE agent_reasoning TYPE datetime DEFAULT time::now();

-- ═══════════════════════════════════════════════════════════════════════════════
-- PHASE 2: NEW EDGE TYPES (Relationship Tables)
-- ═══════════════════════════════════════════════════════════════════════════════

-- informs_reasoning: Links decision to its reasoning chain
-- Example: decision -> informs_reasoning -> agent_reasoning
CREATE TABLE IF NOT EXISTS informs_reasoning SCHEMALESS;
DEFINE FIELD in ON TABLE informs_reasoning TYPE string;  -- decision id
DEFINE FIELD out ON TABLE informs_reasoning TYPE string;  -- agent_reasoning id
DEFINE FIELD created_at ON TABLE informs_reasoning TYPE datetime DEFAULT time::now();

-- challenges_lesson: Detect when decisions challenge or refine existing lessons
-- Challenge types: contradicts (opposes), limits (constrains), refines (improves), extends (broadens)
-- Severity levels: major (breaks lesson), minor (edge case), clarification (better understanding)
CREATE TABLE IF NOT EXISTS challenges_lesson SCHEMALESS;
DEFINE FIELD in ON TABLE challenges_lesson TYPE string;  -- decision id
DEFINE FIELD out ON TABLE challenges_lesson TYPE string;  -- lesson id
DEFINE FIELD challenge_type ON TABLE challenges_lesson TYPE string;  -- contradicts|limits|refines|extends
DEFINE FIELD severity ON TABLE challenges_lesson TYPE string;  -- major|minor|clarification
DEFINE FIELD notes ON TABLE challenges_lesson TYPE string;  -- Human-readable explanation
DEFINE FIELD created_at ON TABLE challenges_lesson TYPE datetime DEFAULT time::now();

-- relates_to_decision: Track how decisions impact downstream decisions
-- Dependency types: blocks (must resolve first), enables (makes possible), refines (improves), contradicts (opposes)
-- Impact levels: critical (can't proceed), significant (requires redesign), minor (minor adjustment)
CREATE TABLE IF NOT EXISTS relates_to_decision SCHEMALESS;
DEFINE FIELD in ON TABLE relates_to_decision TYPE string;  -- source decision id
DEFINE FIELD out ON TABLE relates_to_decision TYPE string;  -- dependent decision id
DEFINE FIELD dependency_type ON TABLE relates_to_decision TYPE string;  -- blocks|enables|refines|contradicts
DEFINE FIELD impact_level ON TABLE relates_to_decision TYPE string;  -- critical|significant|minor
DEFINE FIELD notes ON TABLE relates_to_decision TYPE string;  -- Explanation
DEFINE FIELD created_at ON TABLE relates_to_decision TYPE datetime DEFAULT time::now();

-- validates_reasoning: Link reasoning assumptions to lessons that validate them
-- Used for: "Does operational evidence (lessons) validate our reasoning assumptions?"
CREATE TABLE IF NOT EXISTS validates_reasoning SCHEMALESS;
DEFINE FIELD in ON TABLE validates_reasoning TYPE string;  -- lesson id
DEFINE FIELD out ON TABLE validates_reasoning TYPE string;  -- agent_reasoning id
DEFINE FIELD validation_strength ON TABLE validates_reasoning TYPE string;  -- strong|moderate|weak
DEFINE FIELD notes ON TABLE validates_reasoning TYPE string;
DEFINE FIELD created_at ON TABLE validates_reasoning TYPE datetime DEFAULT time::now();

-- ═══════════════════════════════════════════════════════════════════════════════
-- PHASE 2: NEW INDEXES (7 total for performance)
-- ═══════════════════════════════════════════════════════════════════════════════

-- agent_reasoning indexes
CREATE INDEX IF NOT EXISTS idx_reasoning_decision ON TABLE agent_reasoning COLUMNS decision_id;
CREATE INDEX IF NOT EXISTS idx_reasoning_confidence ON TABLE agent_reasoning COLUMNS confidence_score DESC;
CREATE INDEX IF NOT EXISTS idx_reasoning_type ON TABLE agent_reasoning COLUMNS reasoning_type;
CREATE INDEX IF NOT EXISTS idx_reasoning_composite ON TABLE agent_reasoning COLUMNS reasoning_type, confidence_score DESC;

-- challenges_lesson indexes
CREATE INDEX IF NOT EXISTS idx_challenges_decision ON TABLE challenges_lesson COLUMNS in;
CREATE INDEX IF NOT EXISTS idx_challenges_lesson ON TABLE challenges_lesson COLUMNS out;
CREATE INDEX IF NOT EXISTS idx_challenges_severity ON TABLE challenges_lesson COLUMNS severity;

-- relates_to_decision indexes
CREATE INDEX IF NOT EXISTS idx_relates_source ON TABLE relates_to_decision COLUMNS in;
CREATE INDEX IF NOT EXISTS idx_relates_target ON TABLE relates_to_decision COLUMNS out;
CREATE INDEX IF NOT EXISTS idx_relates_impact ON TABLE relates_to_decision COLUMNS impact_level;

-- Edge relationship indexes
CREATE INDEX IF NOT EXISTS idx_informs_reasoning_edge ON TABLE informs_reasoning COLUMNS in;
CREATE INDEX IF NOT EXISTS idx_validates_reasoning_edge ON TABLE validates_reasoning COLUMNS out;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PHASE 2: QUERY PATTERNS (Reference Implementation)
-- ═══════════════════════════════════════════════════════════════════════════════

-- Query Pattern 1: Root Cause Analysis
-- Goal: Find the reasoning chain that led to a decision
-- Usage: SELECT reasoning details for a decision to understand WHY it was made
-- Pattern: decision -> informs_reasoning -> agent_reasoning
-- SELECT * FROM agent_reasoning WHERE decision_id = $decision_id;

-- Query Pattern 2: Contradiction Detection
-- Goal: Find lessons that contradict recent decisions
-- Usage: Identify when operational evidence (lessons) contradicts our reasoning
-- Pattern: decision -> challenges_lesson -> lesson
-- SELECT challenges_lesson.*, lesson FROM challenges_lesson
-- WHERE challenges_lesson.severity = 'major' AND in IN (
--   SELECT decision:out FROM has_decisions WHERE in = $session_id
-- );

-- Query Pattern 3: Decision Cascades
-- Goal: Trace how one decision affects downstream decisions
-- Usage: Understand impact propagation when a critical decision changes
-- Pattern: decision -> relates_to_decision -> decision (recursive)
-- SELECT * FROM relates_to_decision WHERE in = $decision_id;
-- THEN recursively fetch where in = $dependent_decision_id;

-- Query Pattern 4: High-Confidence Reasoning
-- Goal: Find decisions made with high confidence and strong reasoning
-- Usage: Identify stable, well-justified decisions for reuse in similar contexts
-- Pattern: agent_reasoning with confidence_score >= 0.8
-- SELECT * FROM agent_reasoning WHERE confidence_score >= 0.8 ORDER BY confidence_score DESC;

-- ═══════════════════════════════════════════════════════════════════════════════
-- PHASE 1 REFERENCE (for context, don't modify)
-- ═══════════════════════════════════════════════════════════════════════════════

-- Phase 1 tables (existing):
-- - session: Top-level agent execution session
-- - decision: Critical decision point during execution
-- - action: Specific function call or tool invocation
-- - outcome: Final result(s) of a session
-- - lesson: Extracted learning from session
-- - has_decisions, has_actions, has_outcomes: Session relationships
-- - informs_actions: Decisions inform which actions
-- - validates_lesson: Outcomes validated by lessons
-- - relates_to_paper: Sessions relate to research papers
-- - derives_from_research: Decisions derived from papers

-- Phase 1 already has:
-- - 14 existing tables
-- - 31 existing indexes
-- - Comprehensive query patterns
-- - Full test coverage (51/51 tests passing)

-- Phase 2 adds:
-- + 1 new node type (agent_reasoning)
-- + 4 new edge types (informs_reasoning, challenges_lesson, relates_to_decision, validates_reasoning)
-- + 12 new indexes for performance
-- + 4 new query patterns for analysis

-- ═══════════════════════════════════════════════════════════════════════════════
-- SCHEMA STATISTICS
-- ═══════════════════════════════════════════════════════════════════════════════

-- Phase 1 + Phase 2 Combined:
-- - Node types: 6 (session, decision, action, outcome, lesson, agent_reasoning)
-- - Edge types: 10 (has_decisions, has_actions, has_outcomes, informs_actions,
--                   validates_lesson, relates_to_paper, derives_from_research,
--                   informs_reasoning, challenges_lesson, relates_to_decision,
--                   validates_reasoning)
-- - Total tables: 18
-- - Total indexes: 43 (31 from Phase 1 + 12 from Phase 2)
-- - Total query patterns: 7 documented

-- ═══════════════════════════════════════════════════════════════════════════════
-- INTEGRATION NOTES
-- ═══════════════════════════════════════════════════════════════════════════════

-- Phase 2 Extension Points:
-- 1. MCP Tools (next phase): record_reasoning, record_challenge, record_cascade
-- 2. Query integration: All 7 patterns become MCP tools
-- 3. Test coverage: New tests for 4 new edge types + reasoning validation
-- 4. Documentation: Add Phase 2 query patterns to MCP tool docs

-- Performance Considerations:
-- - agent_reasoning: Indexed on confidence_score for filtering high-confidence reasoning
-- - challenges_lesson: Indexed on severity for prioritizing major contradictions
-- - relates_to_decision: Indexed on impact_level for cascade impact analysis
-- - Composite indexes on reasoning_type + confidence for multi-field queries

-- Future Extensions (Phase 3+):
-- - Automatic contradiction detection (decisions vs lessons)
-- - Reasoning confidence trending (track confidence over time)
-- - Decision impact forecasting (predict cascades)
-- - Reasoning pattern extraction (identify common reasoning chains)

-- ═══════════════════════════════════════════════════════════════════════════════
