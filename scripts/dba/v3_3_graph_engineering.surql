-- ==============================================================================
-- SurrealDB 3.3.0 Graph Engineering Schema: Kaggle Recursive Knowledge Graph
-- Enables multi-hop GraphRAG traversal across active Kaggle competitions,
-- mathematical/physical invariants, AutoHarness policies, kernels, and scores.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Node Tables
-- ------------------------------------------------------------------------------

-- Competitions / Targets
DEFINE TABLE OVERWRITE kaggle_competition TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE slug               ON kaggle_competition TYPE string;
DEFINE FIELD OVERWRITE title              ON kaggle_competition TYPE string;
DEFINE FIELD OVERWRITE prize_pool         ON kaggle_competition TYPE option<string>;
DEFINE FIELD OVERWRITE deadline           ON kaggle_competition TYPE option<string>;
DEFINE FIELD OVERWRITE metric             ON kaggle_competition TYPE option<string>;
DEFINE FIELD OVERWRITE current_best_score ON kaggle_competition TYPE option<float>;
DEFINE FIELD OVERWRITE target_score       ON kaggle_competition TYPE option<float>;
DEFINE FIELD OVERWRITE status             ON kaggle_competition TYPE string DEFAULT 'active';
DEFINE FIELD OVERWRITE created_at         ON kaggle_competition TYPE option<datetime | string> DEFAULT time::now();

DEFINE INDEX OVERWRITE idx_competition_slug   ON kaggle_competition FIELDS slug;
DEFINE INDEX OVERWRITE idx_competition_status ON kaggle_competition FIELDS status;

-- Invariants (Physical, Mathematical, Topological)
DEFINE TABLE OVERWRITE kaggle_invariant TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE code             ON kaggle_invariant TYPE string;
DEFINE FIELD OVERWRITE title            ON kaggle_invariant TYPE string;
DEFINE FIELD OVERWRITE description      ON kaggle_invariant TYPE string;
DEFINE FIELD OVERWRITE domain           ON kaggle_invariant TYPE string;
DEFINE FIELD OVERWRITE formal_rule      ON kaggle_invariant TYPE option<string>;
DEFINE FIELD OVERWRITE created_at       ON kaggle_invariant TYPE option<datetime | string> DEFAULT time::now();

DEFINE INDEX OVERWRITE idx_invariant_code   ON kaggle_invariant FIELDS code UNIQUE;
DEFINE INDEX OVERWRITE idx_invariant_domain ON kaggle_invariant FIELDS domain;

-- AutoHarness Policies (Deterministic Code-as-Action Verifiers)
DEFINE TABLE OVERWRITE autoharness_policy TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE name               ON autoharness_policy TYPE string;
DEFINE FIELD OVERWRITE description        ON autoharness_policy TYPE string;
DEFINE FIELD OVERWRITE ast_rule           ON autoharness_policy TYPE option<string>;
DEFINE FIELD OVERWRITE zero_cost_latency  ON autoharness_policy TYPE option<float>;
DEFINE FIELD OVERWRITE created_at         ON autoharness_policy TYPE option<datetime | string> DEFAULT time::now();

DEFINE INDEX OVERWRITE idx_policy_name ON autoharness_policy FIELDS name UNIQUE;

-- Kaggle Kernels (Dispatched Notebooks / Runtimes)
DEFINE TABLE OVERWRITE kaggle_kernel TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE kernel_slug   ON kaggle_kernel TYPE string;
DEFINE FIELD OVERWRITE competition   ON kaggle_kernel TYPE string;
DEFINE FIELD OVERWRITE hardware      ON kaggle_kernel TYPE string;
DEFINE FIELD OVERWRITE last_status   ON kaggle_kernel TYPE string;
DEFINE FIELD OVERWRITE created_at    ON kaggle_kernel TYPE option<datetime | string> DEFAULT time::now();

DEFINE INDEX OVERWRITE idx_kernel_slug ON kaggle_kernel FIELDS kernel_slug UNIQUE;

-- Leaderboard Scores
DEFINE TABLE OVERWRITE kaggle_score TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE value        ON kaggle_score TYPE float;
DEFINE FIELD OVERWRITE metric       ON kaggle_score TYPE string;
DEFINE FIELD OVERWRITE score_type   ON kaggle_score TYPE string DEFAULT 'public';
DEFINE FIELD OVERWRITE recorded_at  ON kaggle_score TYPE option<datetime | string> DEFAULT time::now();

DEFINE INDEX OVERWRITE idx_score_metric ON kaggle_score FIELDS metric;


-- ------------------------------------------------------------------------------
-- 2. Graph Relation Tables (TYPE RELATION)
-- ------------------------------------------------------------------------------

-- Competition -> HAS_INVARIANT -> Invariant
DEFINE TABLE OVERWRITE has_invariant TYPE RELATION
    IN kaggle_competition OUT kaggle_invariant SCHEMALESS;
DEFINE FIELD OVERWRITE priority   ON has_invariant TYPE option<int> DEFAULT 1;
DEFINE FIELD OVERWRITE created_at ON has_invariant TYPE option<datetime | string> DEFAULT time::now();
DEFINE INDEX OVERWRITE idx_uniq_has_invariant ON has_invariant FIELDS in, out UNIQUE;

-- AutoHarness Policy -> ENFORCES -> Invariant
DEFINE TABLE OVERWRITE enforces_invariant TYPE RELATION
    IN autoharness_policy OUT kaggle_invariant SCHEMALESS;
DEFINE FIELD OVERWRITE verification_mode ON enforces_invariant TYPE option<string> DEFAULT 'ast_compile';
DEFINE FIELD OVERWRITE created_at        ON enforces_invariant TYPE option<datetime | string> DEFAULT time::now();
DEFINE INDEX OVERWRITE idx_uniq_enforces_invariant ON enforces_invariant FIELDS in, out UNIQUE;

-- Kernel -> EMBEDS_POLICY -> AutoHarness Policy
DEFINE TABLE OVERWRITE embeds_policy TYPE RELATION
    IN kaggle_kernel OUT autoharness_policy SCHEMALESS;
DEFINE FIELD OVERWRITE active     ON embeds_policy TYPE option<bool> DEFAULT true;
DEFINE FIELD OVERWRITE created_at ON embeds_policy TYPE option<datetime | string> DEFAULT time::now();
DEFINE INDEX OVERWRITE idx_uniq_embeds_policy ON embeds_policy FIELDS in, out UNIQUE;

-- Kernel -> TARGETS -> Competition
DEFINE TABLE OVERWRITE targets_competition TYPE RELATION
    IN kaggle_kernel OUT kaggle_competition SCHEMALESS;
DEFINE FIELD OVERWRITE primary    ON targets_competition TYPE option<bool> DEFAULT true;
DEFINE FIELD OVERWRITE created_at ON targets_competition TYPE option<datetime | string> DEFAULT time::now();
DEFINE INDEX OVERWRITE idx_uniq_targets_competition ON targets_competition FIELDS in, out UNIQUE;

-- Kernel -> GENERATED -> Submission Record
DEFINE TABLE OVERWRITE generated_submission TYPE RELATION
    IN kaggle_kernel OUT submission_record SCHEMALESS;
DEFINE FIELD OVERWRITE created_at ON generated_submission TYPE option<datetime | string> DEFAULT time::now();
DEFINE INDEX OVERWRITE idx_uniq_generated_submission ON generated_submission FIELDS in, out UNIQUE;

-- Submission Record -> YIELDED_SCORE -> Kaggle Score
DEFINE TABLE OVERWRITE yielded_score TYPE RELATION
    IN submission_record OUT kaggle_score SCHEMALESS;
DEFINE FIELD OVERWRITE verified   ON yielded_score TYPE option<bool> DEFAULT true;
DEFINE FIELD OVERWRITE created_at ON yielded_score TYPE option<datetime | string> DEFAULT time::now();
DEFINE INDEX OVERWRITE idx_uniq_yielded_score ON yielded_score FIELDS in, out UNIQUE;

-- Learning -> APPLIES_TO -> Competition
DEFINE TABLE OVERWRITE applies_to TYPE RELATION
    IN learning OUT kaggle_competition SCHEMALESS;
DEFINE FIELD OVERWRITE confidence ON applies_to TYPE option<float> DEFAULT 1.0;
DEFINE FIELD OVERWRITE created_at ON applies_to TYPE option<datetime | string> DEFAULT time::now();
DEFINE INDEX OVERWRITE idx_uniq_applies_to ON applies_to FIELDS in, out UNIQUE;

-- Learning -> DERIVED_FROM -> Submission Record | Kernel
DEFINE TABLE OVERWRITE derived_from TYPE RELATION
    IN learning OUT submission_record | kaggle_kernel | kaggle_score SCHEMALESS;
DEFINE FIELD OVERWRITE context    ON derived_from TYPE option<string>;
DEFINE FIELD OVERWRITE created_at ON derived_from TYPE option<datetime | string> DEFAULT time::now();

-- Learning -> TRANSFERS_TO -> Competition (Cross-competition transfer learning)
DEFINE TABLE OVERWRITE transfers_to TYPE RELATION
    IN learning OUT kaggle_competition SCHEMALESS;
DEFINE FIELD OVERWRITE transfer_mechanism ON transfers_to TYPE option<string>;
DEFINE FIELD OVERWRITE created_at         ON transfers_to TYPE option<datetime | string> DEFAULT time::now();
DEFINE INDEX OVERWRITE idx_uniq_transfers_to ON transfers_to FIELDS in, out UNIQUE;

