-- SurrealDB Schema Migration - Phase 1 Fix #1
-- Created: 2026-02-14
-- Purpose: Create foundation tables for decision analysis system

-- Table 1: decisions
-- Stores all decisions from vault with metadata
DEFINE TABLE decisions SCHEMAFULL;

-- Core fields
DEFINE FIELD id ON TABLE decisions TYPE string;
DEFINE FIELD title ON TABLE decisions TYPE string;
DEFINE FIELD description ON TABLE decisions TYPE string;
DEFINE FIELD chosen_option ON TABLE decisions TYPE string;

-- Reasoning and confidence
DEFINE FIELD rationale ON TABLE decisions TYPE string;
DEFINE FIELD reasoning_type ON TABLE decisions TYPE string;
DEFINE FIELD confidence_score ON TABLE decisions TYPE number;

-- Decision tracking
DEFINE FIELD status ON TABLE decisions TYPE string;
DEFINE FIELD timestamp ON TABLE decisions TYPE datetime;

-- Alternatives and assumptions (optional arrays)
DEFINE FIELD alternatives_rejected ON TABLE decisions TYPE array;
DEFINE FIELD assumptions ON TABLE decisions TYPE array;

-- Links and metadata
DEFINE FIELD related_papers ON TABLE decisions TYPE array;
DEFINE FIELD related_lessons ON TABLE decisions TYPE array;

-- Audit trail
DEFINE FIELD created_at ON TABLE decisions TYPE datetime;
DEFINE FIELD updated_at ON TABLE decisions TYPE datetime;
DEFINE FIELD created_by ON TABLE decisions TYPE string;

-- Table 2: decision_cascades
-- Stores impact relationships between decisions
DEFINE TABLE decision_cascades SCHEMAFULL;

DEFINE FIELD id ON TABLE decision_cascades TYPE string;

-- Relationship identifiers
DEFINE FIELD source_decision_id ON TABLE decision_cascades TYPE string;
DEFINE FIELD target_decision_id ON TABLE decision_cascades TYPE string;

-- Relationship metadata
DEFINE FIELD dependency_type ON TABLE decision_cascades TYPE string;
DEFINE FIELD impact_level ON TABLE decision_cascades TYPE string;
DEFINE FIELD description ON TABLE decision_cascades TYPE string;
DEFINE FIELD impact_score ON TABLE decision_cascades TYPE number;

-- Tracking
DEFINE FIELD depth ON TABLE decision_cascades TYPE number;
DEFINE FIELD discovered_at ON TABLE decision_cascades TYPE datetime;

-- Table 3: decision_contradictions
-- Stores detected contradictions between decisions and evidence
DEFINE TABLE decision_contradictions SCHEMAFULL;

DEFINE FIELD id ON TABLE decision_contradictions TYPE string;

-- Relationship identifiers
DEFINE FIELD decision_id ON TABLE decision_contradictions TYPE string;
DEFINE FIELD lesson_id ON TABLE decision_contradictions TYPE string;

-- Contradiction metadata
DEFINE FIELD challenge_type ON TABLE decision_contradictions TYPE string;
DEFINE FIELD severity ON TABLE decision_contradictions TYPE string;
DEFINE FIELD description ON TABLE decision_contradictions TYPE string;
DEFINE FIELD detection_method ON TABLE decision_contradictions TYPE string;

-- Analysis
DEFINE FIELD embedding_similarity ON TABLE decision_contradictions TYPE number;
DEFINE FIELD detected_at ON TABLE decision_contradictions TYPE datetime;

-- Table 4: decision_impacts
-- Stores computed impacts from cascade analysis
DEFINE TABLE decision_impacts SCHEMAFULL;

DEFINE FIELD id ON TABLE decision_impacts TYPE string;

-- Relationship identifiers
DEFINE FIELD source_decision_id ON TABLE decision_impacts TYPE string;
DEFINE FIELD target_decision_id ON TABLE decision_impacts TYPE string;

-- Impact analysis
DEFINE FIELD depth ON TABLE decision_impacts TYPE number;
DEFINE FIELD impact_type ON TABLE decision_impacts TYPE string;
DEFINE FIELD impact_score ON TABLE decision_impacts TYPE number;

-- Path information
DEFINE FIELD path ON TABLE decision_impacts TYPE array;
DEFINE FIELD computed_at ON TABLE decision_impacts TYPE datetime;
