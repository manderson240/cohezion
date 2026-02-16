-- SurrealDB Performance Indexes - Phase 1 Fix #1
-- Created: 2026-02-14
-- Purpose: Add performance indexes on foreign key relationships

-- Indexes for decision_cascades lookups
DEFINE INDEX cascade_source_idx ON TABLE decision_cascades COLUMNS source_decision_id;
DEFINE INDEX cascade_target_idx ON TABLE decision_cascades COLUMNS target_decision_id;

-- Indexes for decision_contradictions lookups
DEFINE INDEX contradiction_decision_idx ON TABLE decision_contradictions COLUMNS decision_id;

-- Indexes for decision_impacts lookups
DEFINE INDEX impact_source_idx ON TABLE decision_impacts COLUMNS source_decision_id;

-- Composite index for common queries
DEFINE INDEX cascade_pair_idx ON TABLE decision_cascades COLUMNS (source_decision_id, target_decision_id);
