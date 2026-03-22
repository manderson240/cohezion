-- Traces: [NFR-3]
-- SurrealDB 3.0 Schema: The Three Pillars of institutional Memory

-- PILLAR 1: DECISIONS
-- Capture finalized agent actions and consensus events
DEFINE TABLE decisions SCHEMAFULL;
DEFINE FIELD agent_id ON TABLE decisions TYPE string;
DEFINE FIELD intent_id ON TABLE decisions TYPE string;
DEFINE FIELD z_vector_512 ON TABLE decisions TYPE array<float>;
DEFINE FIELD z_vector_512[*] ON TABLE decisions TYPE float;
DEFINE FIELD physical_state_12 ON TABLE decisions TYPE array<float>;
DEFINE FIELD physical_state_12[*] ON TABLE decisions TYPE float;
DEFINE FIELD human_readable_intent ON TABLE decisions TYPE string;
DEFINE FIELD coherence_score ON TABLE decisions TYPE float;
DEFINE FIELD timestamp ON TABLE decisions TYPE datetime DEFAULT time::now();
DEFINE FIELD provenance_hash ON TABLE decisions TYPE string;

DEFINE INDEX idx_decision_vector ON TABLE decisions 
    FIELDS z_vector_512 HNSW DIMENSION 512 DIST COSINE EFC 200 M 16;

-- PILLAR 2: EXPERIMENTS
-- Capture TDD failures, research drafts, and divergent evolutions
DEFINE TABLE experiments SCHEMAFULL;
DEFINE FIELD type ON TABLE experiments TYPE string;
DEFINE FIELD agent_id ON TABLE experiments TYPE string;
DEFINE FIELD content_hash ON TABLE experiments TYPE string;
DEFINE FIELD z_vector_512 ON TABLE experiments TYPE array<float>;
DEFINE FIELD z_vector_512[*] ON TABLE experiments TYPE float;
DEFINE FIELD state_snapshot ON TABLE experiments TYPE object;
DEFINE FIELD metrics ON TABLE experiments TYPE object;
DEFINE FIELD coherence_score ON TABLE experiments TYPE float;
DEFINE FIELD provenance_hash ON TABLE experiments TYPE string;
DEFINE FIELD timestamp ON TABLE experiments TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_experiment_hash ON TABLE experiments FIELDS content_hash UNIQUE;
DEFINE INDEX idx_experiment_vector ON TABLE experiments
    FIELDS z_vector_512 HNSW DIMENSION 512 DIST COSINE EFC 200 M 16;

-- PILLAR 3: PATTERNS
-- Capture discovered latent shapes and recurring coherence structures
DEFINE TABLE patterns SCHEMAFULL;
DEFINE FIELD name ON TABLE patterns TYPE string;
DEFINE FIELD agent_id ON TABLE patterns TYPE string;
DEFINE FIELD z_vector_512 ON TABLE patterns TYPE array<float>;
DEFINE FIELD z_vector_512[*] ON TABLE patterns TYPE float;
DEFINE FIELD content_hash ON TABLE patterns TYPE string;
DEFINE FIELD validation_status ON TABLE patterns TYPE string DEFAULT 'pending';
DEFINE FIELD discovery_source ON TABLE patterns TYPE string;
DEFINE FIELD coherence_score ON TABLE patterns TYPE float;
DEFINE FIELD provenance_hash ON TABLE patterns TYPE string;
DEFINE FIELD timestamp ON TABLE patterns TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_pattern_vector ON TABLE patterns 
    FIELDS z_vector_512 HNSW DIMENSION 512 DIST COSINE EFC 250 M 20;
