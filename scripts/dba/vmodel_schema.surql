-- SurrealDB 3.0 Schema: V-Model Traceability (Session 96b)
-- Systems Engineering verification lifecycle for agentic compound loop
--
-- Database: cohezion:main
-- V-Model gates connect left branch (nondeterministic agent work)
-- to right branch (deterministic verification) via hash-locked DRRs.
--
-- Reference: VP-Model (vp-model.vercel.app), arXiv:2502.13184v1
-- Bi-temporal: valid_from/valid_to (domain) + VERSION clause (system-time)

-- ─────────────────────────────────────────────────────────────────
-- V-MODEL GATES (Design Review Reports at each lifecycle transition)
-- ─────────────────────────────────────────────────────────────────
DEFINE TABLE vmodel_gate SCHEMAFULL;

-- Gate identity
DEFINE FIELD gate_id       ON vmodel_gate TYPE string;
DEFINE FIELD level         ON vmodel_gate TYPE string
    ASSERT level IN ["intent", "plan", "architecture", "implementation"];
DEFINE FIELD gate_name     ON vmodel_gate TYPE string DEFAULT '';

-- Left branch artifact (nondeterministic: plan, spec, code)
DEFINE FIELD left_artifact   ON vmodel_gate TYPE string;
DEFINE FIELD artifact_hash   ON vmodel_gate TYPE string;

-- Right branch artifact (deterministic: test, review, retrospection)
DEFINE FIELD right_artifact  ON vmodel_gate TYPE string;
DEFINE FIELD test_hash       ON vmodel_gate TYPE string;

-- Gate verdict
DEFINE FIELD passed          ON vmodel_gate TYPE bool DEFAULT false;
DEFINE FIELD drr_summary     ON vmodel_gate TYPE string DEFAULT '';
DEFINE FIELD boundary_mismatches   ON vmodel_gate TYPE int DEFAULT 0;
DEFINE FIELD abstraction_gaps      ON vmodel_gate TYPE int DEFAULT 0;
DEFINE FIELD dependency_violations ON vmodel_gate TYPE int DEFAULT 0;

-- Provenance
DEFINE FIELD session_id    ON vmodel_gate TYPE string;
DEFINE FIELD agent_id      ON vmodel_gate TYPE option<string>;

-- Bi-temporal
DEFINE FIELD valid_from    ON vmodel_gate TYPE datetime DEFAULT time::now();
DEFINE FIELD valid_to      ON vmodel_gate TYPE option<datetime>;
DEFINE FIELD created_at    ON vmodel_gate TYPE datetime DEFAULT time::now();

-- Indexes
DEFINE INDEX idx_gate_id      ON vmodel_gate FIELDS gate_id;
DEFINE INDEX idx_gate_level   ON vmodel_gate FIELDS level;
DEFINE INDEX idx_gate_session ON vmodel_gate FIELDS session_id;
DEFINE INDEX idx_gate_passed  ON vmodel_gate FIELDS passed;
DEFINE INDEX idx_gate_temporal ON vmodel_gate FIELDS valid_from, valid_to;

-- ─────────────────────────────────────────────────────────────────
-- TRACEABILITY LINKS (requirement ↔ test ↔ outcome)
-- ─────────────────────────────────────────────────────────────────
DEFINE TABLE traces SCHEMAFULL;

DEFINE FIELD requirement_id  ON traces TYPE string;
DEFINE FIELD test_id         ON traces TYPE string;
DEFINE FIELD trace_type      ON traces TYPE string
    ASSERT trace_type IN ["satisfies", "verifies", "validates", "contradicts"];
DEFINE FIELD confidence      ON traces TYPE float DEFAULT 1.0
    ASSERT confidence >= 0.0 AND confidence <= 1.0;
DEFINE FIELD evidence        ON traces TYPE string DEFAULT '';

-- Links to V-Model gate that established this trace
DEFINE FIELD gate            ON traces TYPE option<record<vmodel_gate>> REFERENCE;

-- Bi-temporal
DEFINE FIELD valid_from      ON traces TYPE datetime DEFAULT time::now();
DEFINE FIELD valid_to        ON traces TYPE option<datetime>;
DEFINE FIELD created_at      ON traces TYPE datetime DEFAULT time::now();

-- Indexes
DEFINE INDEX idx_trace_req    ON traces FIELDS requirement_id;
DEFINE INDEX idx_trace_test   ON traces FIELDS test_id;
DEFINE INDEX idx_trace_type   ON traces FIELDS trace_type;
DEFINE INDEX idx_trace_temporal ON traces FIELDS valid_from, valid_to;

-- ─────────────────────────────────────────────────────────────────
-- HASH CHAIN (tamper-evident audit trail for agent decisions)
-- Addresses OLIF risk (agents fabricating audit evidence)
-- ─────────────────────────────────────────────────────────────────
DEFINE TABLE hash_chain SCHEMAFULL;

DEFINE FIELD chain_id      ON hash_chain TYPE string;
DEFINE FIELD sequence      ON hash_chain TYPE int;
DEFINE FIELD prev_hash     ON hash_chain TYPE string;
DEFINE FIELD payload_hash  ON hash_chain TYPE string;
DEFINE FIELD chain_hash    ON hash_chain TYPE string;
DEFINE FIELD payload_type  ON hash_chain TYPE string
    ASSERT payload_type IN ["journey_transition", "gate_verdict", "skill_mutation", "retrospection"];
DEFINE FIELD payload_ref   ON hash_chain TYPE string;
DEFINE FIELD created_at    ON hash_chain TYPE datetime DEFAULT time::now();

-- Indexes
DEFINE INDEX idx_chain_id    ON hash_chain FIELDS chain_id;
DEFINE INDEX idx_chain_seq   ON hash_chain FIELDS chain_id, sequence UNIQUE;
DEFINE INDEX idx_chain_type  ON hash_chain FIELDS payload_type;

-- ─────────────────────────────────────────────────────────────────
-- PROOF OBLIGATIONS (deterministic invariant checks)
-- Records pass/fail of physics and logical invariants
-- ─────────────────────────────────────────────────────────────────
DEFINE TABLE proof_obligation SCHEMAFULL;

DEFINE FIELD obligation_id   ON proof_obligation TYPE string;
DEFINE FIELD invariant_name  ON proof_obligation TYPE string;
DEFINE FIELD invariant_type  ON proof_obligation TYPE string
    ASSERT invariant_type IN ["physics", "logical", "constitutional", "architectural"];
DEFINE FIELD expression      ON proof_obligation TYPE string;
DEFINE FIELD passed          ON proof_obligation TYPE bool;
DEFINE FIELD actual_value    ON proof_obligation TYPE option<float>;
DEFINE FIELD expected_bound  ON proof_obligation TYPE option<float>;
DEFINE FIELD tolerance       ON proof_obligation TYPE option<float>;
DEFINE FIELD error_message   ON proof_obligation TYPE string DEFAULT '';

-- Links to gate and journey
DEFINE FIELD gate            ON proof_obligation TYPE option<record<vmodel_gate>> REFERENCE;
DEFINE FIELD journey_id      ON proof_obligation TYPE option<string>;

-- Temporal
DEFINE FIELD created_at      ON proof_obligation TYPE datetime DEFAULT time::now();

-- Indexes
DEFINE INDEX idx_proof_name   ON proof_obligation FIELDS invariant_name;
DEFINE INDEX idx_proof_type   ON proof_obligation FIELDS invariant_type;
DEFINE INDEX idx_proof_passed ON proof_obligation FIELDS passed;
