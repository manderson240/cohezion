-- SurrealDB Schema: Genesis Engine — Total Artifact Persistence
-- Purpose: Store ALL artifacts, internal states, prompts, and model outputs
--          for future analysis, world model training, and universe reconstruction.
--
-- Design Principle: Nothing is ephemeral. SurrealDB = Akashic Records.
--
-- SurrealDB 3.0 compatibility notes (migrated 2026-04-09):
--   - FLEXIBLE TYPE object syntax removed; use TYPE object (schemaless within field)
--   - Optional fields use TYPE none | <type> syntax (option<T> parses but doesn't override)
--   - Re-applying existing fields requires DEFINE FIELD OVERWRITE
--   - Live views (DEFINE TABLE AS SELECT) do not support ORDER BY; sort at query time
--
-- Tables:
--   1. journey_transitions    — (state, action, next_state, reward) for world model training
--   2. universe_snapshots     — Illustris-style periodic full-state captures
--   3. prompt_artifacts       — Every prompt/response pair with full context
--   4. model_artifacts        — Every checkpoint with hyperparameters and lineage
--   5. simulation_artifacts   — Every simulation run with trajectory data
--   6. internal_state_snapshots — Periodic captures of ALL system state

USE NS cohezion DB genesis;

-- ============================================================================
-- TABLE: journey_transitions
-- Purpose: World model training data — (s, a, s', r) tuples per step
-- Inspired by: LeWorldModel (LeCun/JEPA, arxiv 2603.19312)
-- ============================================================================

DEFINE TABLE journey_transitions SCHEMAFULL;

DEFINE FIELD step_id ON journey_transitions TYPE string;
DEFINE FIELD journey_id ON journey_transitions TYPE string;
DEFINE FIELD t ON journey_transitions TYPE int;
DEFINE FIELD state_12d ON journey_transitions TYPE array;
DEFINE FIELD action_embedding ON journey_transitions TYPE array;
DEFINE FIELD next_state_12d ON journey_transitions TYPE array;
DEFINE FIELD reward ON journey_transitions TYPE float;
DEFINE FIELD spinor_bloch ON journey_transitions TYPE array;
DEFINE FIELD tempic_vector ON journey_transitions TYPE array;
DEFINE FIELD fiber_base ON journey_transitions TYPE array;
DEFINE FIELD fiber_internal ON journey_transitions TYPE array;
DEFINE FIELD entropy_production ON journey_transitions TYPE float;
DEFINE FIELD topology_h0 ON journey_transitions TYPE int;
DEFINE FIELD topology_h1 ON journey_transitions TYPE int;
DEFINE FIELD alternatives_considered ON journey_transitions TYPE object;
DEFINE FIELD context_snapshot ON journey_transitions TYPE string;
DEFINE FIELD model_id ON journey_transitions TYPE string;
DEFINE FIELD token_count ON journey_transitions TYPE int;
DEFINE FIELD latency_ms ON journey_transitions TYPE float;
DEFINE FIELD timestamp ON journey_transitions TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_journey_transitions_journey ON journey_transitions FIELDS journey_id;
DEFINE INDEX idx_journey_transitions_time ON journey_transitions FIELDS timestamp;

-- ============================================================================
-- TABLE: universe_snapshots
-- Purpose: Illustris-style time-series of global universe state
-- Periodic full captures for epoch browsing and cosmic evolution tracking
-- ============================================================================

DEFINE TABLE universe_snapshots SCHEMAFULL;

DEFINE FIELD snapshot_id ON universe_snapshots TYPE string;
DEFINE FIELD tick ON universe_snapshots TYPE int;
DEFINE FIELD timestamp ON universe_snapshots TYPE datetime DEFAULT time::now();
DEFINE FIELD global_coherence ON universe_snapshots TYPE float;
DEFINE FIELD global_entropy ON universe_snapshots TYPE float;
DEFINE FIELD global_free_energy ON universe_snapshots TYPE float;
DEFINE FIELD symmetry_group ON universe_snapshots TYPE string;
DEFINE FIELD temperature ON universe_snapshots TYPE float;
DEFINE FIELD n_agents ON universe_snapshots TYPE int;
DEFINE FIELD topology_summary ON universe_snapshots TYPE object;
DEFINE FIELD fisher_eigenvalue_max ON universe_snapshots TYPE float;
DEFINE FIELD order_parameters ON universe_snapshots TYPE object;
DEFINE FIELD cosmogony_stage ON universe_snapshots TYPE int;

DEFINE INDEX idx_universe_snapshots_tick ON universe_snapshots FIELDS tick;
DEFINE INDEX idx_universe_snapshots_time ON universe_snapshots FIELDS timestamp;

-- ============================================================================
-- TABLE: prompt_artifacts
-- Purpose: Every prompt/response pair with full internal state context
-- Enables retrospective analysis of decision-making quality
-- ============================================================================

DEFINE TABLE prompt_artifacts SCHEMAFULL;

DEFINE FIELD artifact_id ON prompt_artifacts TYPE string;
DEFINE FIELD journey_id ON prompt_artifacts TYPE option<string>;
DEFINE FIELD step_id ON prompt_artifacts TYPE option<string>;
DEFINE FIELD prompt_text ON prompt_artifacts TYPE string;
DEFINE FIELD response_text ON prompt_artifacts TYPE string;
DEFINE FIELD model_id ON prompt_artifacts TYPE string;
DEFINE FIELD internal_state_before ON prompt_artifacts TYPE none | object;
DEFINE FIELD internal_state_after ON prompt_artifacts TYPE none | object;
DEFINE FIELD sampling_temperature ON prompt_artifacts TYPE none | float;
DEFINE FIELD top_p ON prompt_artifacts TYPE none | float;
DEFINE FIELD token_count_prompt ON prompt_artifacts TYPE int;
DEFINE FIELD token_count_completion ON prompt_artifacts TYPE int;
DEFINE FIELD latency_ms ON prompt_artifacts TYPE float;
DEFINE FIELD confidence ON prompt_artifacts TYPE float;
DEFINE FIELD reasoning_chain ON prompt_artifacts TYPE none | object;
DEFINE FIELD timestamp ON prompt_artifacts TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_prompt_artifacts_journey ON prompt_artifacts FIELDS journey_id;
DEFINE INDEX idx_prompt_artifacts_model ON prompt_artifacts FIELDS model_id;
DEFINE INDEX idx_prompt_artifacts_time ON prompt_artifacts FIELDS timestamp;

-- ============================================================================
-- TABLE: model_artifacts
-- Purpose: Every model checkpoint with hyperparameters and lineage
-- Enables model genealogy tracking (which checkpoint spawned which)
-- ============================================================================

DEFINE TABLE model_artifacts SCHEMAFULL;

DEFINE FIELD artifact_id ON model_artifacts TYPE string;
DEFINE FIELD model_type ON model_artifacts TYPE string;
DEFINE FIELD version ON model_artifacts TYPE string;
DEFINE FIELD checkpoint_path ON model_artifacts TYPE string;
DEFINE FIELD hyperparameters ON model_artifacts TYPE object;
DEFINE FIELD training_loss_curve ON model_artifacts TYPE array;
DEFINE FIELD validation_metrics ON model_artifacts TYPE object;
DEFINE FIELD dataset_id ON model_artifacts TYPE option<string>;
DEFINE FIELD parent_artifact_id ON model_artifacts TYPE option<string>;
DEFINE FIELD created_at ON model_artifacts TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_model_artifacts_type ON model_artifacts FIELDS model_type;
DEFINE INDEX idx_model_artifacts_parent ON model_artifacts FIELDS parent_artifact_id;

-- ============================================================================
-- TABLE: simulation_artifacts
-- Purpose: Every simulation run with trajectory data and divergence metrics
-- ============================================================================

DEFINE TABLE simulation_artifacts SCHEMAFULL;

DEFINE FIELD sim_id ON simulation_artifacts TYPE string;
DEFINE FIELD simulator_type ON simulation_artifacts TYPE string;
DEFINE FIELD initial_conditions ON simulation_artifacts TYPE object;
DEFINE FIELD trajectory_data ON simulation_artifacts TYPE object;
DEFINE FIELD divergence_from_real ON simulation_artifacts TYPE float;
DEFINE FIELD duration_steps ON simulation_artifacts TYPE int;
DEFINE FIELD compute_time_ms ON simulation_artifacts TYPE float;
DEFINE FIELD physics_engines_used ON simulation_artifacts TYPE array;
DEFINE FIELD audio_waveform_summary ON simulation_artifacts TYPE option<string>;
DEFINE FIELD video_thumbnail_path ON simulation_artifacts TYPE option<string>;
DEFINE FIELD narration_text ON simulation_artifacts TYPE option<string>;
DEFINE FIELD created_at ON simulation_artifacts TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_simulation_artifacts_type ON simulation_artifacts FIELDS simulator_type;

-- ============================================================================
-- TABLE: internal_state_snapshots
-- Purpose: Periodic full-state captures of the ENTIRE system
-- The most complete record — captures everything at a moment in time
-- ============================================================================

DEFINE TABLE internal_state_snapshots SCHEMAFULL;

DEFINE FIELD snapshot_id ON internal_state_snapshots TYPE string;
DEFINE FIELD timestamp ON internal_state_snapshots TYPE datetime DEFAULT time::now();
DEFINE FIELD all_agent_states ON internal_state_snapshots TYPE object;
DEFINE FIELD all_spinor_states ON internal_state_snapshots TYPE object;
DEFINE FIELD fiber_bundle_state ON internal_state_snapshots TYPE object;
DEFINE FIELD gauge_field_strengths ON internal_state_snapshots TYPE object;
DEFINE FIELD thermodynamic_state ON internal_state_snapshots TYPE object;
DEFINE FIELD topology_state ON internal_state_snapshots TYPE object;
DEFINE FIELD cosmogony_stage ON internal_state_snapshots TYPE object;
DEFINE FIELD fisher_metric_snapshot ON internal_state_snapshots TYPE object;
DEFINE FIELD active_journeys_count ON internal_state_snapshots TYPE int;
DEFINE FIELD total_transitions_recorded ON internal_state_snapshots TYPE int;

DEFINE INDEX idx_internal_snapshots_time ON internal_state_snapshots FIELDS timestamp;

-- ============================================================================
-- VIEWS for analysis
-- ============================================================================

-- Universe evolution timeline (Illustris-style)
-- NOTE: SurrealDB 3.0 live views do not support ORDER BY; sort at query time.
DEFINE TABLE universe_evolution_view AS
  SELECT
    tick,
    timestamp,
    global_coherence,
    global_entropy,
    symmetry_group,
    temperature,
    n_agents,
    cosmogony_stage
  FROM universe_snapshots;

-- Training data quality summary
DEFINE TABLE training_data_summary AS
  SELECT
    journey_id,
    count() AS transition_count,
    math::mean(reward) AS avg_reward,
    math::min(reward) AS min_reward,
    math::max(reward) AS max_reward
  FROM journey_transitions
  GROUP BY journey_id;
