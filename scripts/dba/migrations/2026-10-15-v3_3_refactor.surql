-- ==============================================================================
-- Migration: 2026-10-15-v3_3_refactor.surql
-- SurrealDB 3.3.0 Knowledge & Memory Table Refactor
-- Applies Tri-Temporal, Vector HNSW (256D & 12D), and Composite Indexing
-- ==============================================================================

-- Phase 1: Pre-migration data normalization
-- Migrate qualitative string descriptor records in `learning` to state_12d_descriptor
UPDATE learning 
SET state_12d_descriptor = vector_12d, 
    vector_12d = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
WHERE type::is_string(vector_12d) = true;

-- Backfill transaction_time and valid_from on existing learning records if missing
UPDATE learning 
SET transaction_time = time::now(),
    valid_from = IF created_at != NONE THEN created_at ELSE time::now() END
WHERE transaction_time = NONE;

-- Phase 2: Apply table declarations and fields for learning
DEFINE TABLE OVERWRITE learning TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE title                 ON learning TYPE option<string>;
DEFINE FIELD OVERWRITE summary               ON learning TYPE option<string>;
DEFINE FIELD OVERWRITE description           ON learning TYPE option<string>;
DEFINE FIELD OVERWRITE category              ON learning TYPE option<string>;
DEFINE FIELD OVERWRITE tags                  ON learning TYPE option<array<string>>;
DEFINE FIELD OVERWRITE number                ON learning TYPE option<int>;
DEFINE FIELD OVERWRITE confidence            ON learning TYPE option<float> ASSERT $value == NONE OR ($value >= 0f AND $value <= 1f);
DEFINE FIELD OVERWRITE state_12d_descriptor  ON learning TYPE option<string>;
DEFINE FIELD OVERWRITE transaction_time      ON learning TYPE option<datetime> DEFAULT time::now();
DEFINE FIELD OVERWRITE valid_from            ON learning TYPE option<datetime> DEFAULT time::now();
DEFINE FIELD OVERWRITE valid_to              ON learning TYPE option<datetime>;
DEFINE FIELD OVERWRITE superseded_by         ON learning TYPE option<record<learning>>;
DEFINE FIELD OVERWRITE created_at            ON learning TYPE option<datetime | string> DEFAULT time::now();
DEFINE FIELD OVERWRITE embedding             ON learning TYPE option<array<float>>;
DEFINE FIELD OVERWRITE vector_12d            ON learning TYPE option<array<float>>;

DEFINE INDEX OVERWRITE idx_learning_embedding ON learning
    FIELDS embedding
    HNSW DIMENSION 256
    DIST COSINE
    TYPE F32
    EFC 150 M 12 M0 24;

DEFINE INDEX OVERWRITE idx_learning_vector_12d ON learning
    FIELDS vector_12d
    HNSW DIMENSION 12
    DIST COSINE
    TYPE F32
    EFC 100 M 12 M0 24;

DEFINE INDEX OVERWRITE idx_learning_created_at        ON learning FIELDS created_at;
DEFINE INDEX OVERWRITE idx_learning_category_created  ON learning FIELDS category, created_at;
DEFINE INDEX OVERWRITE idx_learning_valid_from        ON learning FIELDS valid_from;
DEFINE INDEX OVERWRITE idx_learning_valid_to          ON learning FIELDS valid_to;
DEFINE INDEX OVERWRITE idx_learning_number            ON learning FIELDS number;

-- Phase 3: Apply kanban_item definitions
DEFINE TABLE OVERWRITE kanban_item TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE title           ON kanban_item TYPE option<string>;
DEFINE FIELD OVERWRITE status          ON kanban_item TYPE option<string>;
DEFINE FIELD OVERWRITE priority        ON kanban_item TYPE any;
DEFINE FIELD OVERWRITE category        ON kanban_item TYPE option<string>;
DEFINE FIELD OVERWRITE domain          ON kanban_item TYPE option<string>;
DEFINE FIELD OVERWRITE type            ON kanban_item TYPE option<string>;
DEFINE FIELD OVERWRITE source          ON kanban_item TYPE option<string>;
DEFINE FIELD OVERWRITE notes           ON kanban_item TYPE option<string>;
DEFINE FIELD OVERWRITE assigned_agent  ON kanban_item TYPE option<string>;
DEFINE FIELD OVERWRITE created_at      ON kanban_item TYPE option<datetime | string>;
DEFINE FIELD OVERWRITE updated_at      ON kanban_item TYPE option<datetime | string> DEFAULT time::now();

DEFINE INDEX OVERWRITE idx_kanban_status         ON kanban_item FIELDS status;
DEFINE INDEX OVERWRITE idx_kanban_status_created ON kanban_item FIELDS status, created_at;
DEFINE INDEX OVERWRITE idx_kanban_domain         ON kanban_item FIELDS domain;
DEFINE INDEX OVERWRITE idx_kanban_category       ON kanban_item FIELDS category;

-- Phase 4: Apply experiment_run definitions
DEFINE TABLE OVERWRITE experiment_run TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE experiment_id   ON experiment_run TYPE option<string>;
DEFINE FIELD OVERWRITE name            ON experiment_run TYPE option<string>;
DEFINE FIELD OVERWRITE status          ON experiment_run TYPE option<string>;
DEFINE FIELD OVERWRITE kind            ON experiment_run TYPE option<string>;
DEFINE FIELD OVERWRITE coherence_score ON experiment_run TYPE option<float> ASSERT $value == NONE OR ($value >= 0f AND $value <= 1f);
DEFINE FIELD OVERWRITE created_at      ON experiment_run TYPE option<datetime | string> DEFAULT time::now();
DEFINE FIELD OVERWRITE timestamp       ON experiment_run TYPE option<float | datetime | string>;

DEFINE INDEX OVERWRITE idx_experiment_status         ON experiment_run FIELDS status;
DEFINE INDEX OVERWRITE idx_experiment_created        ON experiment_run FIELDS created_at;
DEFINE INDEX OVERWRITE idx_experiment_status_created ON experiment_run FIELDS status, created_at;

-- Phase 5: Apply automerge_log definitions
DEFINE TABLE OVERWRITE automerge_log TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE pr                    ON automerge_log TYPE option<string>;
DEFINE FIELD OVERWRITE pr_number             ON automerge_log TYPE option<int>;
DEFINE FIELD OVERWRITE status                ON automerge_log TYPE option<string>;
DEFINE FIELD OVERWRITE merge_commit          ON automerge_log TYPE option<string>;
DEFINE FIELD OVERWRITE head                  ON automerge_log TYPE option<string>;
DEFINE FIELD OVERWRITE gates_passed          ON automerge_log TYPE option<array<string>>;
DEFINE FIELD OVERWRITE gates_failed          ON automerge_log TYPE option<array<string>>;
DEFINE FIELD OVERWRITE timestamp             ON automerge_log TYPE option<datetime | string> DEFAULT time::now();
DEFINE FIELD OVERWRITE created_at            ON automerge_log TYPE option<datetime | string> DEFAULT time::now();

DEFINE INDEX OVERWRITE idx_automerge_status    ON automerge_log FIELDS status;
DEFINE INDEX OVERWRITE idx_automerge_timestamp ON automerge_log FIELDS timestamp;

-- Phase 6: Apply vault_neuron definitions
DEFINE TABLE OVERWRITE vault_neuron TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE task_id         ON vault_neuron TYPE option<string>;
DEFINE FIELD OVERWRITE category        ON vault_neuron TYPE option<string>;
DEFINE FIELD OVERWRITE quality_score   ON vault_neuron TYPE option<float> ASSERT $value == NONE OR ($value >= 0f AND $value <= 1f);
DEFINE FIELD OVERWRITE success         ON vault_neuron TYPE option<bool>;
DEFINE FIELD OVERWRITE node            ON vault_neuron TYPE option<string>;
DEFINE FIELD OVERWRITE model           ON vault_neuron TYPE option<string>;
DEFINE FIELD OVERWRITE tokens          ON vault_neuron TYPE option<int>;
DEFINE FIELD OVERWRITE elapsed_ms      ON vault_neuron TYPE option<int>;
DEFINE FIELD OVERWRITE recorded_at     ON vault_neuron TYPE option<datetime | string> DEFAULT time::now();

DEFINE INDEX OVERWRITE idx_vault_neuron_category_recorded ON vault_neuron FIELDS category, recorded_at;
DEFINE INDEX OVERWRITE idx_vault_neuron_success           ON vault_neuron FIELDS success;
DEFINE INDEX OVERWRITE idx_vault_neuron_node              ON vault_neuron FIELDS node;
DEFINE INDEX OVERWRITE idx_vault_neuron_task_id           ON vault_neuron FIELDS task_id;

-- Phase 7: Apply gaia_kaggle_daemon definitions
DEFINE TABLE OVERWRITE gaia_kaggle_daemon TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE track_slug        ON gaia_kaggle_daemon TYPE option<string>;
DEFINE FIELD OVERWRITE display_name      ON gaia_kaggle_daemon TYPE option<string>;
DEFINE FIELD OVERWRITE submission_status ON gaia_kaggle_daemon TYPE option<string>;
DEFINE FIELD OVERWRITE hardware_target   ON gaia_kaggle_daemon TYPE option<string>;
DEFINE FIELD OVERWRITE assigned_model    ON gaia_kaggle_daemon TYPE option<string>;
DEFINE FIELD OVERWRITE latest_score      ON gaia_kaggle_daemon TYPE option<float>;
DEFINE FIELD OVERWRITE timestamp         ON gaia_kaggle_daemon TYPE option<datetime | string>;

DEFINE INDEX OVERWRITE idx_gaia_status    ON gaia_kaggle_daemon FIELDS submission_status;
DEFINE INDEX OVERWRITE idx_gaia_timestamp ON gaia_kaggle_daemon FIELDS timestamp;

-- Phase 8: Apply submission_record definitions
DEFINE TABLE OVERWRITE submission_record TYPE NORMAL SCHEMALESS;
DEFINE FIELD OVERWRITE competition    ON submission_record TYPE option<string>;
DEFINE FIELD OVERWRITE kernel         ON submission_record TYPE option<string>;
DEFINE FIELD OVERWRITE kernel_version ON submission_record TYPE option<int>;
DEFINE FIELD OVERWRITE status         ON submission_record TYPE option<string>;
DEFINE FIELD OVERWRITE submitted_at   ON submission_record TYPE option<datetime | string> DEFAULT time::now();

DEFINE INDEX OVERWRITE idx_sub_competition_submitted ON submission_record FIELDS competition, submitted_at;
DEFINE INDEX OVERWRITE idx_sub_status                ON submission_record FIELDS status;
