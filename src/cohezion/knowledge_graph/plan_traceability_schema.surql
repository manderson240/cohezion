-- SurrealDB Schema: Plan Traceability Graph
-- Purpose: Track plan lifecycle with graph edges linking plans -> tasks -> files -> commits.
-- Namespace/DB: cohezion/traceability
--
-- Tables:
--   1. plan              -- A development plan (from .claude/plans/ or docs/plans/)
--   2. task              -- A step within a plan
--   3. file              -- A file touched during plan execution
--   4. commit            -- A git commit produced during plan execution
--   5. plan_has_task     -- Edge: plan -> task
--   6. task_modifies     -- Edge: task -> file
--   7. commit_implements -- Edge: commit -> task
--   8. commit_touches    -- Edge: commit -> file

USE NS cohezion DB traceability;

-- ============================================================================
-- TABLE: plan
-- ============================================================================

DEFINE TABLE plan SCHEMAFULL;

DEFINE FIELD name ON plan TYPE string;
DEFINE FIELD slug ON plan TYPE string;
DEFINE FIELD status ON plan TYPE string
    ASSERT $value IN ["draft", "approved", "in_progress", "completed", "abandoned"];
DEFINE FIELD created_at ON plan TYPE datetime DEFAULT time::now();
DEFINE FIELD completed_at ON plan TYPE option<datetime>;
DEFINE FIELD source_file ON plan TYPE string;
DEFINE FIELD archived_from ON plan TYPE option<string>;
DEFINE FIELD tasks_total ON plan TYPE int DEFAULT 0;
DEFINE FIELD tasks_completed ON plan TYPE int DEFAULT 0;
DEFINE FIELD session_id ON plan TYPE option<string>;

DEFINE INDEX idx_plan_slug ON plan FIELDS slug UNIQUE;

-- ============================================================================
-- TABLE: task
-- ============================================================================

DEFINE TABLE task SCHEMAFULL;

DEFINE FIELD title ON task TYPE string;
DEFINE FIELD status ON task TYPE string
    ASSERT $value IN ["pending", "in_progress", "completed", "skipped"];
DEFINE FIELD step_number ON task TYPE string;
DEFINE FIELD created_at ON task TYPE datetime DEFAULT time::now();
DEFINE FIELD completed_at ON task TYPE option<datetime>;

DEFINE INDEX idx_task_status ON task FIELDS status;

-- ============================================================================
-- TABLE: file
-- ============================================================================

DEFINE TABLE file SCHEMAFULL;

DEFINE FIELD path ON file TYPE string;
DEFINE FIELD last_modified ON file TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_file_path ON file FIELDS path UNIQUE;

-- ============================================================================
-- TABLE: commit
-- ============================================================================

DEFINE TABLE commit SCHEMAFULL;

DEFINE FIELD hash ON commit TYPE string;
DEFINE FIELD message ON commit TYPE string;
DEFINE FIELD timestamp ON commit TYPE datetime DEFAULT time::now();
DEFINE FIELD author ON commit TYPE string DEFAULT "mike-anderson";

DEFINE INDEX idx_commit_hash ON commit FIELDS hash UNIQUE;

-- ============================================================================
-- EDGE TABLES (graph relationships)
-- ============================================================================

DEFINE TABLE plan_has_task SCHEMAFULL;
DEFINE TABLE task_modifies SCHEMAFULL;
DEFINE TABLE commit_implements SCHEMAFULL;
DEFINE TABLE commit_touches SCHEMAFULL;
