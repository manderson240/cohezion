-- SurrealDB Schema for Universe Artifact Management
-- Part of Cohezion's Knowledge Graph System
-- Designed to preserve universe simulation artifacts discovered in Phase 0-1

-- ============================================================================
-- NAMESPACE & DATABASE SETUP
-- ============================================================================

USE NS cohezion DB core;

-- ============================================================================
-- TABLE: universe_training_runs
-- Purpose: Catalog all universe training/simulation runs
-- Indexed for: fast lookup by timestamp, model version, coherence score
-- ============================================================================

DEFINE TABLE universe_training_runs SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR update ALLOW (user_id = $auth.id)
    FOR delete ALLOW false;

DEFINE FIELD run_id ON universe_training_runs TYPE string UNIQUE;
DEFINE FIELD timestamp ON universe_training_runs TYPE datetime;
DEFINE FIELD model_id ON universe_training_runs TYPE string;
DEFINE FIELD model_version ON universe_training_runs TYPE string;
DEFINE FIELD universe_epoch ON universe_training_runs TYPE int;
DEFINE FIELD coherence_score ON universe_training_runs TYPE float;
DEFINE FIELD total_artifacts ON universe_training_runs TYPE int;
DEFINE FIELD total_size_bytes ON universe_training_runs TYPE int;
DEFINE FIELD training_duration_seconds ON universe_training_runs TYPE float;
DEFINE FIELD language_drift_rate ON universe_training_runs TYPE float;
DEFINE FIELD extraction_status ON universe_training_runs TYPE string DEFAULT 'pending';
DEFINE FIELD git_commit ON universe_training_runs TYPE string;
DEFINE FIELD notes ON universe_training_runs TYPE string;
DEFINE FIELD created_at ON universe_training_runs TYPE datetime DEFAULT now();
DEFINE FIELD updated_at ON universe_training_runs TYPE datetime DEFAULT now();

DEFINE INDEX idx_run_timestamp ON universe_training_runs COLUMNS timestamp;
DEFINE INDEX idx_run_model ON universe_training_runs COLUMNS model_id;
DEFINE INDEX idx_run_epoch ON universe_training_runs COLUMNS universe_epoch;
DEFINE INDEX idx_run_status ON universe_training_runs COLUMNS extraction_status;

-- ============================================================================
-- TABLE: universe_artifacts
-- Purpose: Store individual artifact files with metadata
-- Indexed for: fast lookup by run, type, language pattern
-- Size: ~97MB of training data across 200+ files
-- ============================================================================

DEFINE TABLE universe_artifacts SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR update ALLOW (user_id = $auth.id)
    FOR delete ALLOW false;

DEFINE FIELD artifact_id ON universe_artifacts TYPE string UNIQUE;
DEFINE FIELD run_id ON universe_artifacts TYPE string;
DEFINE FIELD file_path ON universe_artifacts TYPE string;
DEFINE FIELD file_name ON universe_artifacts TYPE string;
DEFINE FIELD artifact_type ON universe_artifacts TYPE string;
DEFINE FIELD file_size_bytes ON universe_artifacts TYPE int;
DEFINE FIELD content_hash ON universe_artifacts TYPE string;
DEFINE FIELD content_compressed ON universe_artifacts TYPE bytes;
DEFINE FIELD language_model_generation ON universe_artifacts TYPE int;
DEFINE FIELD semantic_drift_vector ON universe_artifacts TYPE string;
DEFINE FIELD key_patterns ON universe_artifacts TYPE array;
DEFINE FIELD training_phase ON universe_artifacts TYPE string;
DEFINE FIELD extraction_timestamp ON universe_artifacts TYPE datetime DEFAULT now();
DEFINE FIELD verified ON universe_artifacts TYPE bool DEFAULT false;
DEFINE FIELD verification_hash ON universe_artifacts TYPE string;
DEFINE FIELD notes ON universe_artifacts TYPE string;

DEFINE INDEX idx_artifact_run ON universe_artifacts COLUMNS run_id;
DEFINE INDEX idx_artifact_type ON universe_artifacts COLUMNS artifact_type;
DEFINE INDEX idx_artifact_phase ON universe_artifacts COLUMNS training_phase;
DEFINE INDEX idx_artifact_verified ON universe_artifacts COLUMNS verified;

-- ============================================================================
-- TABLE: artifact_journey_links
-- Purpose: Integration with JourneyTracker - connects artifacts to 12D journeys
-- Links universe simulation artifacts to journey states
-- ============================================================================

DEFINE TABLE artifact_journey_links SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id != NONE)
    FOR update ALLOW (user_id = $auth.id)
    FOR delete ALLOW (user_id = $auth.id);

DEFINE FIELD link_id ON artifact_journey_links TYPE string UNIQUE;
DEFINE FIELD artifact_id ON artifact_journey_links TYPE string;
DEFINE FIELD journey_id ON artifact_journey_links TYPE string;
DEFINE FIELD journey_step ON artifact_journey_links TYPE int;
DEFINE FIELD universe_coordinates ON artifact_journey_links TYPE string;
DEFINE FIELD flume_embedding ON artifact_journey_links TYPE string;
DEFINE FIELD semantic_alignment_score ON artifact_journey_links TYPE float;
DEFINE FIELD decision_context ON artifact_journey_links TYPE string;
DEFINE FIELD agent_coherence_at_step ON artifact_journey_links TYPE float;
DEFINE FIELD timestamp ON artifact_journey_links TYPE datetime DEFAULT now();

DEFINE INDEX idx_journey_link_artifact ON artifact_journey_links COLUMNS artifact_id;
DEFINE INDEX idx_journey_link_journey ON artifact_journey_links COLUMNS journey_id;
DEFINE INDEX idx_journey_link_universe ON artifact_journey_links COLUMNS universe_coordinates;

-- ============================================================================
-- TABLE: artifact_collections
-- Purpose: Organize artifacts into named sets for analysis and retrieval
-- Enables grouped queries (e.g., "all semantic drift artifacts from epoch 5")
-- ============================================================================

DEFINE TABLE artifact_collections SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id != NONE)
    FOR update ALLOW (user_id = $auth.id)
    FOR delete ALLOW (user_id = $auth.id);

DEFINE FIELD collection_id ON artifact_collections TYPE string UNIQUE;
DEFINE FIELD name ON artifact_collections TYPE string;
DEFINE FIELD description ON artifact_collections TYPE string;
DEFINE FIELD artifact_ids ON artifact_collections TYPE array;
DEFINE FIELD collection_type ON artifact_collections TYPE string;
DEFINE FIELD universe_epoch_range ON artifact_collections TYPE string;
DEFINE FIELD total_size_bytes ON artifact_collections TYPE int;
DEFINE FIELD artifact_count ON artifact_collections TYPE int;
DEFINE FIELD created_by ON artifact_collections TYPE string;
DEFINE FIELD created_at ON artifact_collections TYPE datetime DEFAULT now();
DEFINE FIELD updated_at ON artifact_collections TYPE datetime DEFAULT now();
DEFINE FIELD tags ON artifact_collections TYPE array;

DEFINE INDEX idx_collection_type ON artifact_collections COLUMNS collection_type;
DEFINE INDEX idx_collection_epoch ON artifact_collections COLUMNS universe_epoch_range;

-- ============================================================================
-- TABLE: universe_patterns
-- Purpose: Store extracted patterns from artifact analysis
-- Captures language drift, semantic shifts, coherence transitions
-- ============================================================================

DEFINE TABLE universe_patterns SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id != NONE)
    FOR update ALLOW (user_id = $auth.id)
    FOR delete ALLOW (user_id = $auth.id);

DEFINE FIELD pattern_id ON universe_patterns TYPE string UNIQUE;
DEFINE FIELD pattern_name ON universe_patterns TYPE string;
DEFINE FIELD pattern_type ON universe_patterns TYPE string;
DEFINE FIELD description ON universe_patterns TYPE string;
DEFINE FIELD universe_epoch ON universe_patterns TYPE int;
DEFINE FIELD confidence_score ON universe_patterns TYPE float;
DEFINE FIELD affected_artifacts ON universe_patterns TYPE array;
DEFINE FIELD semantic_signature ON universe_patterns TYPE string;
DEFINE FIELD emergence_timestamp ON universe_patterns TYPE datetime;
DEFINE FIELD related_patterns ON universe_patterns TYPE array;
DEFINE FIELD created_at ON universe_patterns TYPE datetime DEFAULT now();

DEFINE INDEX idx_pattern_type ON universe_patterns COLUMNS pattern_type;
DEFINE INDEX idx_pattern_epoch ON universe_patterns COLUMNS universe_epoch;
DEFINE INDEX idx_pattern_confidence ON universe_patterns COLUMNS confidence_score;

-- ============================================================================
-- TABLE: migration_snapshots
-- Purpose: Track migration progress and enable rollback/recovery
-- ============================================================================

DEFINE TABLE migration_snapshots SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id != NONE)
    FOR update ALLOW (user_id = $auth.id)
    FOR delete ALLOW false;

DEFINE FIELD snapshot_id ON migration_snapshots TYPE string UNIQUE;
DEFINE FIELD phase ON migration_snapshots TYPE string;
DEFINE FIELD timestamp ON migration_snapshots TYPE datetime DEFAULT now();
DEFINE FIELD artifacts_processed ON migration_snapshots TYPE int;
DEFINE FIELD artifacts_verified ON migration_snapshots TYPE int;
DEFINE FIELD total_bytes_migrated ON migration_snapshots TYPE int;
DEFINE FIELD status ON migration_snapshots TYPE string;
DEFINE FIELD error_count ON migration_snapshots TYPE int;
DEFINE FIELD duration_seconds ON migration_snapshots TYPE float;
DEFINE FIELD notes ON migration_snapshots TYPE string;

DEFINE INDEX idx_snapshot_phase ON migration_snapshots COLUMNS phase;
DEFINE INDEX idx_snapshot_status ON migration_snapshots COLUMNS status;

-- ============================================================================
-- RELATIONSHIPS (SURREALDB EDGES)
-- ============================================================================

-- Link training runs to their artifacts
DEFINE TABLE run_contains_artifacts SCHEMAFULL
  TYPE RELATION
  FROM universe_training_runs
  TO universe_artifacts;

-- Link artifacts to their patterns
DEFINE TABLE artifact_exhibits_pattern SCHEMAFULL
  TYPE RELATION
  FROM universe_artifacts
  TO universe_patterns;

-- Link collections to artifacts
DEFINE TABLE collection_groups_artifacts SCHEMAFULL
  TYPE RELATION
  FROM artifact_collections
  TO universe_artifacts;

-- ============================================================================
-- VIEWS for Common Queries
-- ============================================================================

-- View: Recent universe evolution summary
DEFINE VIEW recent_universe_evolution AS
  SELECT
    run_id,
    timestamp,
    universe_epoch,
    coherence_score,
    total_artifacts,
    total_size_bytes,
    extraction_status
  FROM universe_training_runs
  WHERE extraction_status = 'completed'
  ORDER BY timestamp DESC
  LIMIT 100;

-- View: Language drift timeline
DEFINE VIEW language_drift_timeline AS
  SELECT
    run_id,
    universe_epoch,
    language_drift_rate,
    timestamp,
    COUNT(->artifact_journey_links) AS linked_journeys
  FROM universe_training_runs
  WHERE extraction_status = 'completed'
  ORDER BY universe_epoch;

-- View: Artifact coverage summary
DEFINE VIEW artifact_coverage_summary AS
  SELECT
    artifact_type,
    COUNT() AS count,
    SUM(file_size_bytes) AS total_size,
    AVG(semantic_drift_vector) AS avg_drift,
    MIN(extraction_timestamp) AS first_extracted,
    MAX(extraction_timestamp) AS last_extracted
  FROM universe_artifacts
  GROUP BY artifact_type;

-- ============================================================================
-- MIGRATION UTILITY PROCEDURES
-- ============================================================================

-- Function to create a new training run record
DEFINE FUNCTION create_universe_training_run(
  $run_id: string,
  $model_id: string,
  $model_version: string,
  $universe_epoch: int,
  $coherence_score: float
) {
  LET $timestamp = now();
  CREATE universe_training_runs SET
    run_id = $run_id,
    timestamp = $timestamp,
    model_id = $model_id,
    model_version = $model_version,
    universe_epoch = $universe_epoch,
    coherence_score = $coherence_score,
    extraction_status = 'pending';
  RETURN LAST;
};

-- Function to mark migration as complete
DEFINE FUNCTION mark_migration_complete(
  $snapshot_id: string,
  $artifacts_processed: int,
  $artifacts_verified: int,
  $total_bytes: int,
  $duration_seconds: float
) {
  UPDATE migration_snapshots SET
    status = 'completed',
    artifacts_processed = $artifacts_processed,
    artifacts_verified = $artifacts_verified,
    total_bytes_migrated = $total_bytes,
    duration_seconds = $duration_seconds
  WHERE snapshot_id = $snapshot_id;
  RETURN LAST;
};

-- ============================================================================
-- SCHEMA VERSION & DOCUMENTATION
-- ============================================================================

/*
SCHEMA METADATA:
  Version: 1.0
  Created: 2026-02-11 (Session 55, Phase 2)
  Purpose: Store universe simulation artifacts for analysis and JourneyTracker integration
  Total Capacity: 500+ training runs, 200K+ artifacts, 100GB+ storage
  Estimated Query Latency: <500ms for indexed queries

DESIGN DECISIONS:
  1. Separated concerns: training runs → artifacts → patterns
  2. Immutable artifact storage (no updates to files after verification)
  3. Compression for binary content (file_compressed field)
  4. JourneyTracker integration via artifact_journey_links table
  5. Collection support for grouped artifact queries
  6. Migration snapshots for recovery/audit trail

FUTURE EXTENSIONS:
  - Full-text search on semantic content
  - Machine learning model performance tracking
  - Universe state reconstruction from artifacts
  - Automated anomaly detection in drift patterns
*/
