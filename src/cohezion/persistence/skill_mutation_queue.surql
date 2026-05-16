-- SurrealDB Schema: SkillMutationQueue — HITL Batching Layer
-- Purpose: Buffer SkillRefiner mutations for human review before they reach
--          skill files. SemanticCache L3 checks human_approval_cache to
--          reuse prior decisions on semantically identical diffs.
--
-- SurrealDB 3.0 compatibility (2026-05-16):
--   - SCHEMAFULL tables; optional fields use option<T>
--   - Enums via ASSERT $value IN [...]
--   - Bi-temporal validity via valid_from / valid_to (matches ?versioned=true pattern)
--   - array<string> for mutation ID lists
--
-- Tables:
--   1. pending_mutations     — SkillRefiner writes here instead of disk
--   2. human_approval_cache  — Memoises human decisions by semantic_hash
--   3. batch_checkpoint      — Session-boundary flush units

USE NS cohezion DB compound;

-- ============================================================================
-- TABLE: pending_mutations
-- SkillRefiner enqueues proposed skill changes here.
-- Status moves: pending → approved|rejected|superseded
-- Bi-temporal: valid_from/valid_to enable time-travel replay of mutation history.
-- ============================================================================

DEFINE TABLE pending_mutations SCHEMAFULL;

DEFINE FIELD id              ON pending_mutations TYPE string;
DEFINE FIELD skill_path      ON pending_mutations TYPE string;
DEFINE FIELD change_type     ON pending_mutations TYPE string
    ASSERT $value IN ["hyperparameter", "architecture", "corpus", "routing"];
DEFINE FIELD diff_text       ON pending_mutations TYPE string;
DEFINE FIELD semantic_hash   ON pending_mutations TYPE string;
DEFINE FIELD proposed_by_agent ON pending_mutations TYPE string;
DEFINE FIELD created_at      ON pending_mutations TYPE datetime DEFAULT time::now();
DEFINE FIELD valid_from      ON pending_mutations TYPE datetime DEFAULT time::now();
DEFINE FIELD valid_to        ON pending_mutations TYPE option<datetime>;
DEFINE FIELD status          ON pending_mutations TYPE string
    ASSERT $value IN ["pending", "approved", "rejected", "superseded"]
    DEFAULT "pending";
DEFINE FIELD batch_id        ON pending_mutations TYPE option<string>;

-- Indexes for the hot query paths
DEFINE INDEX idx_pmut_semantic_hash ON pending_mutations FIELDS semantic_hash;
DEFINE INDEX idx_pmut_skill_path    ON pending_mutations FIELDS skill_path;
DEFINE INDEX idx_pmut_status        ON pending_mutations FIELDS status;
DEFINE INDEX idx_pmut_valid_range   ON pending_mutations FIELDS valid_from, valid_to;
DEFINE INDEX idx_pmut_batch         ON pending_mutations FIELDS batch_id;

-- ============================================================================
-- TABLE: human_approval_cache
-- SemanticCache L3 checks this table before surfacing a mutation to the human.
-- Keyed on semantic_hash so identical diffs in different skill files share a decision.
-- applies_to_pattern is a glob (e.g. "src/cohezion/skills/CODE_REVIEW*") that
-- widens the decision to a family of skills, not just the one originally reviewed.
-- ============================================================================

DEFINE TABLE human_approval_cache SCHEMAFULL;

DEFINE FIELD semantic_hash       ON human_approval_cache TYPE string;
DEFINE FIELD decision            ON human_approval_cache TYPE string
    ASSERT $value IN ["approved", "rejected", "needs_review"];
DEFINE FIELD approved_by         ON human_approval_cache TYPE string;
DEFINE FIELD cached_at           ON human_approval_cache TYPE datetime DEFAULT time::now();
DEFINE FIELD applies_to_pattern  ON human_approval_cache TYPE string;
DEFINE FIELD ttl_seconds         ON human_approval_cache TYPE option<int>;
DEFINE FIELD hit_count           ON human_approval_cache TYPE int DEFAULT 0;
DEFINE FIELD last_hit_at         ON human_approval_cache TYPE option<datetime>;

-- semantic_hash is the primary lookup key — must be unique
DEFINE INDEX idx_happroval_hash     ON human_approval_cache FIELDS semantic_hash UNIQUE;
DEFINE INDEX idx_happroval_decision ON human_approval_cache FIELDS decision;
DEFINE INDEX idx_happroval_cached   ON human_approval_cache FIELDS cached_at;

-- ============================================================================
-- TABLE: batch_checkpoint
-- Mutations are gathered into a batch per session, presented once to the human,
-- then flushed (applied to skill files) or discarded at the session boundary.
-- mutations field holds an array of pending_mutations record IDs.
-- ============================================================================

DEFINE TABLE batch_checkpoint SCHEMAFULL;

DEFINE FIELD batch_id        ON batch_checkpoint TYPE string;
DEFINE FIELD session_id      ON batch_checkpoint TYPE string;
DEFINE FIELD mutations       ON batch_checkpoint TYPE array;
DEFINE FIELD status          ON batch_checkpoint TYPE string
    ASSERT $value IN ["pending", "reviewed", "flushed"]
    DEFAULT "pending";
DEFINE FIELD presented_at    ON batch_checkpoint TYPE option<datetime>;
DEFINE FIELD flushed_at      ON batch_checkpoint TYPE option<datetime>;
DEFINE FIELD mutation_count  ON batch_checkpoint TYPE int DEFAULT 0;
DEFINE FIELD created_at      ON batch_checkpoint TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_batch_id        ON batch_checkpoint FIELDS batch_id UNIQUE;
DEFINE INDEX idx_batch_session   ON batch_checkpoint FIELDS session_id;
DEFINE INDEX idx_batch_status    ON batch_checkpoint FIELDS status;

-- ============================================================================
-- Live aggregation: pending mutation count per skill (informational view)
-- NOTE: SurrealDB 3.0 live views do not support ORDER BY; sort at query time.
-- ============================================================================

DEFINE TABLE pending_mutation_counts AS
    SELECT skill_path, count() AS count
    FROM pending_mutations
    WHERE status = "pending"
    GROUP BY skill_path;
