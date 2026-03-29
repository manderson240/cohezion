-- Luma AMD Speedrun Experiment Tracking Schema

-- Experiment records
DEFINE TABLE experiment SCHEMAFULL;
DEFINE FIELD kernel ON experiment TYPE string;
DEFINE FIELD session_id ON experiment TYPE string;
DEFINE FIELD cycle ON experiment TYPE int;
DEFINE FIELD submission_time ON experiment TYPE datetime;
DEFINE FIELD result_us ON experiment TYPE float;
DEFINE FIELD rank_at_time ON experiment TYPE int;
DEFINE FIELD improvement_pct ON experiment TYPE float;
DEFINE FIELD approach_used ON experiment TYPE string;
DEFINE FIELD per_shape_results ON experiment TYPE option<object>;
DEFINE FIELD notes ON experiment TYPE option<string>;
DEFINE FIELD created_at ON experiment TYPE datetime DEFAULT time::now();

-- Session registry
DEFINE TABLE session SCHEMAFULL;
DEFINE FIELD name ON session TYPE string;
DEFINE FIELD git_worktree ON session TYPE option<string>;
DEFINE FIELD focus_kernel ON session TYPE string;
DEFINE FIELD status ON session TYPE string;
DEFINE FIELD last_submission ON session TYPE datetime;
DEFINE FIELD best_result_us ON session TYPE float;
DEFINE FIELD created_at ON session TYPE datetime DEFAULT time::now();

-- Indexes for fast queries
DEFINE INDEX idx_experiment_kernel ON experiment FIELDS kernel;
DEFINE INDEX idx_experiment_result ON experiment FIELDS result_us;
DEFINE INDEX idx_session_kernel ON session FIELDS focus_kernel;
