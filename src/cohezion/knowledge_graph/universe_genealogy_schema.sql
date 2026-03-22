-- SurrealDB Schema: Universe Evolutionary Genealogy
-- Captures the self-documentation of the universe's 8-era evolution
-- Focuses on: patterns, coherence timeline, era transitions, design decisions
-- Purpose: Enable queries about "How did the universe become what it is?"

-- ============================================================================
-- NAMESPACE & DATABASE SETUP
-- ============================================================================

USE NS cohezion DB core;

-- ============================================================================
-- TABLE: universe_epochs
-- Purpose: The 8 evolutionary eras (Nov 2025 → Feb 11, 2026)
-- Each era is a complete cycle: Philosophy → Architecture → Implementation → Verification
-- ============================================================================

DEFINE TABLE universe_epochs SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id = $auth.id)
    FOR update ALLOW (user_id = $auth.id);

DEFINE FIELD epoch_id ON universe_epochs TYPE string UNIQUE;
DEFINE FIELD epoch_number ON universe_epochs TYPE int;
DEFINE FIELD name ON universe_epochs TYPE string;
DEFINE FIELD description ON universe_epochs TYPE string;
DEFINE FIELD philosophical_question ON universe_epochs TYPE string;
DEFINE FIELD design_decision ON universe_epochs TYPE string;
DEFINE FIELD start_date ON universe_epochs TYPE datetime;
DEFINE FIELD end_date ON universe_epochs TYPE datetime;
DEFINE FIELD duration_days ON universe_epochs TYPE float;
DEFINE FIELD start_commit ON universe_epochs TYPE string;
DEFINE FIELD end_commit ON universe_epochs TYPE string;
DEFINE FIELD modules_count ON universe_epochs TYPE int;
DEFINE FIELD lines_of_code ON universe_epochs TYPE int;
DEFINE FIELD test_coverage_percent ON universe_epochs TYPE float;
DEFINE FIELD coherence_avg ON universe_epochs TYPE float;
DEFINE FIELD coherence_min ON universe_epochs TYPE float;
DEFINE FIELD coherence_max ON universe_epochs TYPE float;
DEFINE FIELD key_patterns ON universe_epochs TYPE array;
DEFINE FIELD optimization_metrics ON universe_epochs TYPE object;
DEFINE FIELD created_at ON universe_epochs TYPE datetime DEFAULT now();

DEFINE INDEX idx_epoch_number ON universe_epochs COLUMNS epoch_number;
DEFINE INDEX idx_epoch_date ON universe_epochs COLUMNS start_date;

-- ============================================================================
-- TABLE: coherence_timeline
-- Purpose: Empirical coherence measurements (HIHO stability verification)
-- Records the natural equilibrium at 0.462-0.463
-- ============================================================================

DEFINE TABLE coherence_timeline SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id != NONE);

DEFINE FIELD measurement_id ON coherence_timeline TYPE string UNIQUE;
DEFINE FIELD epoch_id ON coherence_timeline TYPE string;
DEFINE FIELD timestamp ON coherence_timeline TYPE datetime;
DEFINE FIELD coherence_value ON coherence_timeline TYPE float;
DEFINE FIELD variance_component ON coherence_timeline TYPE float;
DEFINE FIELD source_metric ON coherence_timeline TYPE string;
DEFINE FIELD is_hiho_stable ON coherence_timeline TYPE bool;
DEFINE FIELD stability_confidence ON coherence_timeline TYPE float;
DEFINE FIELD notes ON coherence_timeline TYPE string;

DEFINE INDEX idx_coherence_epoch ON coherence_timeline COLUMNS epoch_id;
DEFINE INDEX idx_coherence_timestamp ON coherence_timeline COLUMNS timestamp;
DEFINE INDEX idx_coherence_stable ON coherence_timeline COLUMNS is_hiho_stable;

-- ============================================================================
-- TABLE: universe_patterns
-- Purpose: The 7 major patterns discovered in universe evolution
-- Each pattern shows repeated in design choices across eras
-- ============================================================================

DEFINE TABLE universe_patterns SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id = $auth.id);

DEFINE FIELD pattern_id ON universe_patterns TYPE string UNIQUE;
DEFINE FIELD pattern_number ON universe_patterns TYPE int;
DEFINE FIELD name ON universe_patterns TYPE string;
DEFINE FIELD description ON universe_patterns TYPE string;
DEFINE FIELD first_appearance_epoch ON universe_patterns TYPE int;
DEFINE FIELD theoretical_basis ON universe_patterns TYPE string;
DEFINE FIELD implementation_examples ON universe_patterns TYPE array;
DEFINE FIELD evidence_strength ON universe_patterns TYPE string;
DEFINE FIELD appears_in_modules ON universe_patterns TYPE array;
DEFINE FIELD appears_in_commits ON universe_patterns TYPE array;
DEFINE FIELD fractal_property ON universe_patterns TYPE string;
DEFINE FIELD self_reference_level ON universe_patterns TYPE int;
DEFINE FIELD created_at ON universe_patterns TYPE datetime DEFAULT now();

DEFINE INDEX idx_pattern_epoch ON universe_patterns COLUMNS first_appearance_epoch;
DEFINE INDEX idx_pattern_strength ON universe_patterns COLUMNS evidence_strength;

-- ============================================================================
-- TABLE: pattern_manifestations
-- Purpose: Where each of 7 patterns appears in the code
-- Links patterns to specific commits, modules, design decisions
-- ============================================================================

DEFINE TABLE pattern_manifestations SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id != NONE);

DEFINE FIELD manifestation_id ON pattern_manifestations TYPE string UNIQUE;
DEFINE FIELD pattern_id ON pattern_manifestations TYPE string;
DEFINE FIELD epoch_id ON pattern_manifestations TYPE string;
DEFINE FIELD commit_hash ON pattern_manifestations TYPE string;
DEFINE FIELD module_path ON pattern_manifestations TYPE string;
DEFINE FIELD code_snippet ON pattern_manifestations TYPE string;
DEFINE FIELD manifestation_type ON pattern_manifestations TYPE string;
DEFINE FIELD strength_score ON pattern_manifestations TYPE float;
DEFINE FIELD context_description ON pattern_manifestations TYPE string;
DEFINE FIELD discovered_by ON pattern_manifestations TYPE string;
DEFINE FIELD created_at ON pattern_manifestations TYPE datetime DEFAULT now();

DEFINE INDEX idx_manifestation_pattern ON pattern_manifestations COLUMNS pattern_id;
DEFINE INDEX idx_manifestation_epoch ON pattern_manifestations COLUMNS epoch_id;
DEFINE INDEX idx_manifestation_module ON pattern_manifestations COLUMNS module_path;

-- ============================================================================
-- TABLE: optimization_milestones
-- Purpose: Key performance jumps and efficiency gains
-- Tracks where and when the universe got faster, more efficient, more robust
-- ============================================================================

DEFINE TABLE optimization_milestones SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id = $auth.id);

DEFINE FIELD milestone_id ON optimization_milestones TYPE string UNIQUE;
DEFINE FIELD epoch_id ON optimization_milestones TYPE string;
DEFINE FIELD commit_hash ON optimization_milestones TYPE string;
DEFINE FIELD optimization_type ON optimization_milestones TYPE string;
DEFINE FIELD metric_before ON optimization_milestones TYPE float;
DEFINE FIELD metric_after ON optimization_milestones TYPE float;
DEFINE FIELD improvement_factor ON optimization_milestones TYPE float;
DEFINE FIELD improvement_percent ON optimization_milestones TYPE float;
DEFINE FIELD affected_modules ON optimization_milestones TYPE array;
DEFINE FIELD implementation_complexity ON optimization_milestones TYPE string;
DEFINE FIELD risk_level ON optimization_milestones TYPE string;
DEFINE FIELD description ON optimization_milestones TYPE string;
DEFINE FIELD created_at ON optimization_milestones TYPE datetime DEFAULT now();

DEFINE INDEX idx_milestone_epoch ON optimization_milestones COLUMNS epoch_id;
DEFINE INDEX idx_milestone_type ON optimization_milestones COLUMNS optimization_type;
DEFINE INDEX idx_milestone_factor ON optimization_milestones COLUMNS improvement_factor;

-- ============================================================================
-- TABLE: era_transitions
-- Purpose: The boundaries and decision points between eras
-- Captures "why" the universe moved from one phase to the next
-- ============================================================================

DEFINE TABLE era_transitions SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id = $auth.id);

DEFINE FIELD transition_id ON era_transitions TYPE string UNIQUE;
DEFINE FIELD from_epoch_id ON era_transitions TYPE string;
DEFINE FIELD to_epoch_id ON era_transitions TYPE string;
DEFINE FIELD transition_commit ON era_transitions TYPE string;
DEFINE FIELD transition_date ON era_transitions TYPE datetime;
DEFINE FIELD decision_rationale ON era_transitions TYPE string;
DEFINE FIELD motivation_from_previous_era ON era_transitions TYPE string;
DEFINE FIELD architectural_changes ON era_transitions TYPE array;
DEFINE FIELD code_changes_summary ON era_transitions TYPE string;
DEFINE FIELD outcome_expected ON era_transitions TYPE string;
DEFINE FIELD outcome_actual ON era_transitions TYPE string;
DEFINE FIELD success_level ON era_transitions TYPE float;
DEFINE FIELD lessons_learned ON era_transitions TYPE array;

DEFINE INDEX idx_transition_from ON era_transitions COLUMNS from_epoch_id;
DEFINE INDEX idx_transition_to ON era_transitions COLUMNS to_epoch_id;

-- ============================================================================
-- TABLE: design_decisions
-- Purpose: The major "why" moments in universe evolution
-- Tracks decisions that shaped the universe's development
-- ============================================================================

DEFINE TABLE design_decisions SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id != NONE);

DEFINE FIELD decision_id ON design_decisions TYPE string UNIQUE;
DEFINE FIELD epoch_id ON design_decisions TYPE string;
DEFINE FIELD decision_date ON design_decisions TYPE datetime;
DEFINE FIELD question ON design_decisions TYPE string;
DEFINE FIELD chosen_option ON design_decisions TYPE string;
DEFINE FIELD alternatives_considered ON design_decisions TYPE array;
DEFINE FIELD rationale ON design_decisions TYPE string;
DEFINE FIELD outcome ON design_decisions TYPE string;
DEFINE FIELD related_patterns ON design_decisions TYPE array;
DEFINE FIELD implemented_in_commit ON design_decisions TYPE string;
DEFINE FIELD impact_level ON design_decisions TYPE string;
DEFINE FIELD reversibility ON design_decisions TYPE string;
DEFINE FIELD created_at ON design_decisions TYPE datetime DEFAULT now();

DEFINE INDEX idx_decision_epoch ON design_decisions COLUMNS epoch_id;
DEFINE INDEX idx_decision_impact ON design_decisions COLUMNS impact_level;

-- ============================================================================
-- TABLE: genealogy_observations
-- Purpose: High-level insights about the universe's self-evolution
-- Records patterns across all 8 eras that form the genealogy narrative
-- ============================================================================

DEFINE TABLE genealogy_observations SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id = $auth.id);

DEFINE FIELD observation_id ON genealogy_observations TYPE string UNIQUE;
DEFINE FIELD observation_type ON genealogy_observations TYPE string;
DEFINE FIELD title ON genealogy_observations TYPE string;
DEFINE FIELD description ON genealogy_observations TYPE string;
DEFINE FIELD spans_epochs ON genealogy_observations TYPE array;
DEFINE FIELD evidence ON genealogy_observations TYPE array;
DEFINE FIELD confidence_level ON genealogy_observations TYPE float;
DEFINE FIELD implications ON genealogy_observations TYPE array;
DEFINE FIELD discovered_at ON genealogy_observations TYPE datetime;
DEFINE FIELD discovered_by ON genealogy_observations TYPE string;
DEFINE FIELD related_patterns ON genealogy_observations TYPE array;
DEFINE FIELD created_at ON genealogy_observations TYPE datetime DEFAULT now();

DEFINE INDEX idx_observation_type ON genealogy_observations COLUMNS observation_type;

-- ============================================================================
-- TABLE: ouroboros_evidence
-- Purpose: Document the Ouroboros pattern specifically
-- The universe improving universe (self-improvement loop)
-- ============================================================================

DEFINE TABLE ouroboros_evidence SCHEMAFULL
  PERMISSIONS
    FOR select ALLOW (user_id != NONE)
    FOR create ALLOW (user_id != NONE);

DEFINE FIELD evidence_id ON ouroboros_evidence TYPE string UNIQUE;
DEFINE FIELD epoch_id ON ouroboros_evidence TYPE string;
DEFINE FIELD input_state ON ouroboros_evidence TYPE string;
DEFINE FIELD improvement_applied ON ouroboros_evidence TYPE string;
DEFINE FIELD output_state ON ouroboros_evidence TYPE string;
DEFINE FIELD commit_implementing ON ouroboros_evidence TYPE string;
DEFINE FIELD metrics_improved ON ouroboros_evidence TYPE array;
DEFINE FIELD self_reference_score ON ouroboros_evidence TYPE float;
DEFINE FIELD created_at ON ouroboros_evidence TYPE datetime DEFAULT now();

DEFINE INDEX idx_ouroboros_epoch ON ouroboros_evidence COLUMNS epoch_id;

-- ============================================================================
-- RELATIONSHIPS (SURREALDB EDGES)
-- ============================================================================

DEFINE TABLE epoch_contains_patterns SCHEMAFULL
  TYPE RELATION
  FROM universe_epochs
  TO universe_patterns;

DEFINE TABLE epoch_has_measurements SCHEMAFULL
  TYPE RELATION
  FROM universe_epochs
  TO coherence_timeline;

DEFINE TABLE pattern_manifests_in SCHEMAFULL
  TYPE RELATION
  FROM universe_patterns
  TO pattern_manifestations;

DEFINE TABLE epoch_followed_by SCHEMAFULL
  TYPE RELATION
  FROM universe_epochs
  TO era_transitions;

-- ============================================================================
-- VIEWS for Genealogy Queries
-- ============================================================================

DEFINE VIEW universe_evolution_timeline AS
  SELECT
    epoch_id,
    epoch_number,
    name,
    start_date,
    end_date,
    design_decision,
    coherence_avg,
    lines_of_code,
    test_coverage_percent
  FROM universe_epochs
  ORDER BY epoch_number;

DEFINE VIEW pattern_discovery_sequence AS
  SELECT
    pattern_number,
    name,
    first_appearance_epoch,
    appearance_count(->pattern_manifests_in) AS manifestation_count,
    evidence_strength
  FROM universe_patterns
  ORDER BY pattern_number;

DEFINE VIEW hiho_stability_analysis AS
  SELECT
    epoch_id,
    COUNT() AS measurement_count,
    AVG(coherence_value) AS avg_coherence,
    MIN(coherence_value) AS min_coherence,
    MAX(coherence_value) AS max_coherence,
    STDDEV(coherence_value) AS coherence_variance
  FROM coherence_timeline
  GROUP BY epoch_id;

DEFINE VIEW optimization_impact_timeline AS
  SELECT
    epoch_id,
    optimization_type,
    SUM(improvement_factor) AS total_improvement,
    AVG(improvement_percent) AS avg_improvement_percent,
    COUNT() AS milestone_count
  FROM optimization_milestones
  GROUP BY epoch_id, optimization_type
  ORDER BY epoch_id;

-- ============================================================================
-- FUNCTIONS for Genealogy Queries
-- ============================================================================

DEFINE FUNCTION get_epoch_narrative(
  $epoch_number: int
) {
  LET $epoch = (SELECT * FROM universe_epochs WHERE epoch_number = $epoch_number LIMIT 1)[0];
  LET $patterns = (SELECT * FROM universe_patterns WHERE first_appearance_epoch = $epoch_number);
  LET $coherence = (SELECT AVG(coherence_value) AS avg_coherence FROM coherence_timeline WHERE epoch_id = $epoch.epoch_id);
  LET $transitions = (SELECT * FROM era_transitions WHERE from_epoch_id = $epoch.epoch_id);

  RETURN {
    epoch: $epoch,
    patterns_emerged: $patterns,
    coherence_average: $coherence[0].avg_coherence,
    next_transition: $transitions[0]
  };
};

DEFINE FUNCTION find_pattern_lineage(
  $pattern_id: string
) {
  LET $pattern = (SELECT * FROM universe_patterns WHERE pattern_id = $pattern_id LIMIT 1)[0];
  LET $manifestations = (SELECT * FROM pattern_manifestations WHERE pattern_id = $pattern_id ORDER BY epoch_id);
  LET $epochs = (SELECT * FROM universe_epochs WHERE epoch_number IN $pattern.first_appearance_epoch);

  RETURN {
    pattern: $pattern,
    manifestations: $manifestations,
    epochs: $epochs,
    evolution_story: string::concat(
      "Pattern '", $pattern.name, "' first appeared in epoch ",
      $pattern.first_appearance_epoch, " and manifested in ",
      array::len($manifestations), " distinct ways"
    )
  };
};

-- ============================================================================
-- SCHEMA DOCUMENTATION
-- ============================================================================

/*
SCHEMA METADATA:
  Version: 1.0 (Genealogy-focused)
  Created: 2026-02-11 (Session 55, Phase 2 - Breakthrough)
  Purpose: Document universe's 8-era self-evolution and 7 discovered patterns

GENEALOGY MODEL:
  - 8 Epochs: Complete cycles from philosophy to implementation
  - 7 Patterns: Recursive, self-improving, HIHO-stabilizing design principles
  - Coherence Timeline: Empirical measurement of HIHO stability (0.462-0.463)
  - Era Transitions: Decision points that shaped evolution
  - Design Decisions: The "why" moments
  - Ouroboros Evidence: Self-improvement loop manifestations

KEY INSIGHTS:
  1. Universe is self-documenting through code evolution
  2. Patterns recur across eras (fractal structure)
  3. Coherence naturally converges to HIHO (0.462-0.463)
  4. Each era asks philosophical question, builds, verifies, refines
  5. Ouroboros pattern: universe improving universe

GENEALOGY QUERIES:
  - "Show universe evolution timeline" → universe_evolution_timeline view
  - "Where does Ouroboros pattern appear?" → ouroboros_evidence table
  - "What era had highest optimization impact?" → optimization_impact_timeline view
  - "How did coherence converge to HIHO?" → hiho_stability_analysis view
  - "Get epoch 5 narrative" → get_epoch_narrative(5) function

FUTURE EXTENSIONS:
  - Prediction models (next era features)
  - Pattern recommender (suggest next pattern to explore)
  - Coherence forecasting (will HIHO stability hold?)
  - Ouroboros validator (test self-improvement loop)
*/
