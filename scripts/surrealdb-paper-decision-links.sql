-- ============================================================================
-- SurrealDB Migration: Paper-Decision Links
-- ============================================================================
-- Purpose: Create bidirectional linking between vault papers and decisions
-- Created: 2026-02-16
-- Phase: 2 (Paper Integration)
-- ============================================================================

-- Define the paper_decision_links table (SCHEMAFULL for type safety)
DEFINE TABLE paper_decision_links SCHEMAFULL;

-- Core relationship fields
DEFINE FIELD paper_id ON TABLE paper_decision_links TYPE string;
DEFINE FIELD decision_id ON TABLE paper_decision_links TYPE string;

-- Link semantics (why paper relates to decision)
DEFINE FIELD link_type ON TABLE paper_decision_links TYPE string;
-- Valid values: "research", "validates", "contradicts", "reference", "evidence"

-- Confidence that this link is meaningful (0.0 - 1.0)
DEFINE FIELD confidence ON TABLE paper_decision_links TYPE number;

-- Excerpt from decision rationale mentioning the paper
DEFINE FIELD mentioned_in ON TABLE paper_decision_links TYPE string;

-- When was this link extracted/discovered
DEFINE FIELD extracted_at ON TABLE paper_decision_links TYPE datetime;

-- ============================================================================
-- Indexes for Query Performance
-- ============================================================================

-- Find all decisions related to a paper
DEFINE INDEX idx_links_by_paper ON TABLE paper_decision_links COLUMNS paper_id;

-- Find all papers referenced by a decision
DEFINE INDEX idx_links_by_decision ON TABLE paper_decision_links COLUMNS decision_id;

-- Composite index for paper + link_type queries
DEFINE INDEX idx_paper_link_type ON TABLE paper_decision_links COLUMNS (paper_id, link_type);

-- High-confidence links (for confidence filtering)
DEFINE INDEX idx_high_confidence_links ON TABLE paper_decision_links COLUMNS confidence;

-- ============================================================================
-- Setup Complete
-- ============================================================================
-- This table enables:
-- 1. Bidirectional discovery (paper → decisions, decision → papers)
-- 2. Link type filtering (show only "validates", etc.)
-- 3. Confidence-based ranking (prioritize high-confidence links)
-- 4. Temporal tracking (when was each link discovered)
-- 5. Extraction audit trail (mentioned_in for validation)
