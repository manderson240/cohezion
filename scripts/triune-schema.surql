-- ============================================================================
-- TRIUNE VAULT SCHEMA — SurrealDB 3.0
-- The Akashic Foundation: Neural, Aboriginal, Physics, and Theosophical layers
-- ============================================================================
-- Created: 2026-03-09
-- Purpose: Define the complete Triune Vault connectome
--
-- Tables:
--   neuron         — every vault note
--   synapse        — every wiki-link (explicit) + latent/dream connections
--   country        — domain clusters (Aboriginal layer)
--   songline       — narrative knowledge paths across Countries
--   kinship        — deeper-than-synapse relationships
--   dream          — daily cross-domain resonance events
--   hiho_event     — coherence fusion events (Physics layer)
--   neuron_history — Akashic Records (Theosophical layer)
-- ============================================================================

-- =========================
-- TABLE: neuron
-- Every vault note is a neuron
-- =========================
DEFINE TABLE neuron SCHEMAFULL;

DEFINE FIELD path ON TABLE neuron TYPE string;
DEFINE FIELD title ON TABLE neuron TYPE string;
DEFINE FIELD aspect ON TABLE neuron TYPE string
  ASSERT $value IN ['knower', 'thinker', 'doer', 'connective'];
DEFINE FIELD activation ON TABLE neuron TYPE float DEFAULT 0.5;
DEFINE FIELD stage ON TABLE neuron TYPE string
  ASSERT $value IN ['embryo', 'growing', 'mature', 'resting', 'composting', 'renewed'];
DEFINE FIELD last_fired ON TABLE neuron TYPE option<datetime>;
DEFINE FIELD cluster_id ON TABLE neuron TYPE option<string>;
DEFINE FIELD synapse_out ON TABLE neuron TYPE int DEFAULT 0;
DEFINE FIELD synapse_in ON TABLE neuron TYPE int DEFAULT 0;
DEFINE FIELD word_count ON TABLE neuron TYPE int DEFAULT 0;
DEFINE FIELD tags ON TABLE neuron TYPE array DEFAULT [];
DEFINE FIELD embedding ON TABLE neuron TYPE option<array>;
DEFINE FIELD created ON TABLE neuron TYPE option<datetime>;
DEFINE FIELD modified ON TABLE neuron TYPE option<datetime>;
DEFINE FIELD directory ON TABLE neuron TYPE option<string>;

-- Indexes for common queries
DEFINE INDEX idx_neuron_path ON TABLE neuron COLUMNS path UNIQUE;
DEFINE INDEX idx_neuron_aspect ON TABLE neuron COLUMNS aspect;
DEFINE INDEX idx_neuron_stage ON TABLE neuron COLUMNS stage;
DEFINE INDEX idx_neuron_cluster ON TABLE neuron COLUMNS cluster_id;
DEFINE INDEX idx_neuron_activation ON TABLE neuron COLUMNS activation;

-- =========================
-- TABLE: synapse
-- Every wiki-link is a synapse (edge table)
-- =========================
DEFINE TABLE synapse SCHEMAFULL TYPE RELATION IN neuron OUT neuron;

DEFINE FIELD weight ON TABLE synapse TYPE float DEFAULT 1.0;
DEFINE FIELD link_type ON TABLE synapse TYPE string DEFAULT 'explicit'
  ASSERT $value IN ['explicit', 'latent', 'dream', 'songline'];
DEFINE FIELD created ON TABLE synapse TYPE option<datetime>;

-- =========================
-- TABLE: country
-- Domain clusters (Aboriginal layer)
-- =========================
DEFINE TABLE country SCHEMAFULL;

DEFINE FIELD name ON TABLE country TYPE string;
DEFINE FIELD description ON TABLE country TYPE option<string>;
DEFINE FIELD elders ON TABLE country TYPE array DEFAULT [];
DEFINE FIELD health ON TABLE country TYPE float DEFAULT 0.5;
DEFINE FIELD centroid ON TABLE country TYPE option<array>;
DEFINE FIELD neuron_count ON TABLE country TYPE int DEFAULT 0;

DEFINE INDEX idx_country_name ON TABLE country COLUMNS name UNIQUE;

-- =========================
-- TABLE: country_kin
-- Kinship between Countries
-- =========================
DEFINE TABLE country_kin SCHEMAFULL TYPE RELATION IN country OUT country;

DEFINE FIELD strength ON TABLE country_kin TYPE float DEFAULT 0.5;
DEFINE FIELD shared_songlines ON TABLE country_kin TYPE int DEFAULT 0;

-- =========================
-- TABLE: songline
-- Narrative knowledge paths across Countries (Aboriginal layer)
-- =========================
DEFINE TABLE songline SCHEMAFULL;

DEFINE FIELD name ON TABLE songline TYPE string;
DEFINE FIELD waypoints ON TABLE songline TYPE array DEFAULT [];
DEFINE FIELD country_crossings ON TABLE songline TYPE array DEFAULT [];
DEFINE FIELD singer ON TABLE songline TYPE string DEFAULT 'system';
DEFINE FIELD walked_count ON TABLE songline TYPE int DEFAULT 0;
DEFINE FIELD created ON TABLE songline TYPE option<datetime>;

DEFINE INDEX idx_songline_name ON TABLE songline COLUMNS name UNIQUE;

-- =========================
-- TABLE: kinship
-- Deeper-than-synapse relationships (Aboriginal layer)
-- =========================
DEFINE TABLE kinship SCHEMAFULL TYPE RELATION IN neuron OUT neuron;

DEFINE FIELD relation ON TABLE kinship TYPE string
  ASSERT $value IN ['elder_younger', 'parent_child', 'moiety'];
DEFINE FIELD obligation ON TABLE kinship TYPE option<string>;
DEFINE FIELD created ON TABLE kinship TYPE option<datetime>;

-- =========================
-- TABLE: dream
-- Cross-domain resonance events (The Dreaming / Everlasting Now)
-- =========================
DEFINE TABLE dream SCHEMAFULL;

DEFINE FIELD date ON TABLE dream TYPE datetime;
DEFINE FIELD neurons ON TABLE dream TYPE array DEFAULT [];
DEFINE FIELD spark ON TABLE dream TYPE option<string>;
DEFINE FIELD aspect_mix ON TABLE dream TYPE array DEFAULT [];
DEFINE FIELD confirmed ON TABLE dream TYPE bool DEFAULT false;
DEFINE FIELD songline_id ON TABLE dream TYPE option<string>;

DEFINE INDEX idx_dream_date ON TABLE dream COLUMNS date;

-- =========================
-- TABLE: hiho_event
-- HIHO coherence fusion events (Physics layer)
-- =========================
DEFINE TABLE hiho_event SCHEMAFULL;

DEFINE FIELD country ON TABLE hiho_event TYPE option<string>;
DEFINE FIELD neurons ON TABLE hiho_event TYPE array DEFAULT [];
DEFINE FIELD coherence_score ON TABLE hiho_event TYPE float;
DEFINE FIELD threshold ON TABLE hiho_event TYPE float DEFAULT 0.7;
DEFINE FIELD insight ON TABLE hiho_event TYPE option<string>;
DEFINE FIELD products ON TABLE hiho_event TYPE array DEFAULT [];
DEFINE FIELD date ON TABLE hiho_event TYPE datetime;

DEFINE INDEX idx_hiho_date ON TABLE hiho_event COLUMNS date;

-- =========================
-- TABLE: neuron_history
-- Akashic Records — eternal history of all events (Theosophical layer)
-- =========================
DEFINE TABLE neuron_history SCHEMAFULL;

DEFINE FIELD neuron ON TABLE neuron_history TYPE option<string>;
DEFINE FIELD event_type ON TABLE neuron_history TYPE string
  ASSERT $value IN ['created', 'edited', 'linked', 'fired', 'dreamed', 'fused', 'composted', 'renewed'];
DEFINE FIELD timestamp ON TABLE neuron_history TYPE datetime;
DEFINE FIELD detail ON TABLE neuron_history TYPE option<string>;

DEFINE INDEX idx_history_neuron ON TABLE neuron_history COLUMNS neuron;
DEFINE INDEX idx_history_type ON TABLE neuron_history COLUMNS event_type;
DEFINE INDEX idx_history_ts ON TABLE neuron_history COLUMNS timestamp;

-- =========================
-- TABLE: belongs_to
-- Neuron -> Country membership (edge)
-- =========================
DEFINE TABLE belongs_to SCHEMAFULL TYPE RELATION IN neuron OUT country;

DEFINE FIELD since ON TABLE belongs_to TYPE option<datetime>;

-- =========================
-- FUNCTIONS
-- =========================

-- Compute lifecycle stage from note properties
DEFINE FUNCTION fn::compute_stage($synapse_count: int, $word_count: int, $activation: float, $days_since_modified: int) {
    IF $synapse_count < 3 AND $word_count < 500 {
        RETURN 'embryo';
    };
    IF $activation < 0.2 AND $days_since_modified > 30 {
        RETURN 'resting';
    };
    IF $synapse_count >= 10 AND $word_count >= 500 {
        RETURN 'mature';
    };
    RETURN 'growing';
};

-- Compute HIHO coherence score for a country
DEFINE FUNCTION fn::compute_coherence($country_name: string) {
    LET $neurons = (SELECT id, activation, synapse_out, synapse_in FROM neuron WHERE cluster_id = $country_name);
    LET $n = array::len($neurons);
    IF $n < 3 {
        RETURN 0.0;
    };
    LET $total_synapses = math::sum($neurons.synapse_out) + math::sum($neurons.synapse_in);
    LET $activation_mean = math::mean($neurons.activation);
    LET $synapse_density = $total_synapses / ($n * ($n - 1));
    RETURN $synapse_density * $activation_mean;
};
