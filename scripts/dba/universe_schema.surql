-- SurrealDB 3.0 Schema: Universe State Space (Bi-Temporal)
-- 12D coherence universe for tracking agent state trajectories
-- Bi-temporal: valid_from/valid_to (simulation time) + VERSION clause (system time)

-- universe_node: Primary node type for 12D universe state vectors
-- Each node represents a point in the multi-dimensional coherence space
DEFINE TABLE universe_node SCHEMAFULL;

DEFINE FIELD node_type ON TABLE universe_node TYPE string DEFAULT "state"
    ASSERT node_type IN ["state", "checkpoint", "milestone", "observation", "decision"];

-- Temporal marker
DEFINE FIELD timestamp ON TABLE universe_node TYPE datetime DEFAULT time::now();

-- Optional content (reasoning, action, observation)
DEFINE FIELD content ON TABLE universe_node TYPE option<string>;
DEFINE FIELD summary ON TABLE universe_node TYPE option<string>;

-- Agent context
DEFINE FIELD agent_id ON TABLE universe_node TYPE option<string>;
DEFINE FIELD session_id ON TABLE universe_node TYPE option<string>;

-- 12D physics coordinates
DEFINE FIELD physics ON TABLE universe_node TYPE object;
DEFINE FIELD physics.x ON TABLE universe_node TYPE float DEFAULT 0.0;
DEFINE FIELD physics.y ON TABLE universe_node TYPE float DEFAULT 0.0;
DEFINE FIELD physics.z ON TABLE universe_node TYPE float DEFAULT 0.0;
DEFINE FIELD physics.time ON TABLE universe_node TYPE float DEFAULT 0.0;
DEFINE FIELD physics.physics ON TABLE universe_node TYPE float DEFAULT 0.5;
DEFINE FIELD physics.biology ON TABLE universe_node TYPE float DEFAULT 0.5;
DEFINE FIELD physics.logic ON TABLE universe_node TYPE float DEFAULT 0.5;
DEFINE FIELD physics.quantum ON TABLE universe_node TYPE float DEFAULT 0.5;
DEFINE FIELD physics.field ON TABLE universe_node TYPE float DEFAULT 0.5;
DEFINE FIELD physics.control ON TABLE universe_node TYPE float DEFAULT 0.5;
DEFINE FIELD physics.novelty ON TABLE universe_node TYPE float DEFAULT 0.5;
DEFINE FIELD physics.precipitation ON TABLE universe_node TYPE float DEFAULT 0.5;

-- Coherence metrics
DEFINE FIELD coherence ON TABLE universe_node TYPE float DEFAULT 0.5
    ASSERT coherence >= 0.0 AND coherence <= 1.0;
DEFINE FIELD phi_score ON TABLE universe_node TYPE float DEFAULT 0.0
    ASSERT phi_score >= 0.0 AND phi_score <= 1.0;

-- Vector embedding for semantic search
DEFINE FIELD embedding ON TABLE universe_node TYPE option<array<float>>;
DEFINE FIELD embedding[*] ON TABLE universe_node TYPE float;

-- Bi-temporal: valid-time (when this state held in the simulated universe)
DEFINE FIELD valid_from ON TABLE universe_node TYPE datetime DEFAULT time::now();
DEFINE FIELD valid_to   ON TABLE universe_node TYPE option<datetime>;

-- Flexible metadata
DEFINE FIELD metadata ON TABLE universe_node TYPE object;

-- Indexes
DEFINE INDEX idx_unode_type ON TABLE universe_node COLUMNS node_type;
DEFINE INDEX idx_unode_temporal ON TABLE universe_node COLUMNS valid_from, valid_to;
DEFINE INDEX idx_unode_timestamp ON TABLE universe_node COLUMNS timestamp;
DEFINE INDEX idx_unode_agent_id ON TABLE universe_node COLUMNS agent_id;
DEFINE INDEX idx_unode_session_id ON TABLE universe_node COLUMNS session_id;
DEFINE INDEX idx_unode_coherence ON TABLE universe_node COLUMNS coherence;

-- HNSW index for state vector similarity
DEFINE INDEX idx_unode_embedding ON TABLE universe_node
    COLUMNS embedding
    HNSW DIMENSION 768 DIST COSINE TYPE F32 EFC 150 M 12;

-- universe_region: Named regions in the 12D space
-- Useful for clustering similar states
DEFINE TABLE universe_region SCHEMAFULL;

DEFINE FIELD name ON TABLE universe_region TYPE string;
DEFINE FIELD description ON TABLE universe_region TYPE option<string>;

-- Bounding box in 12D space (center + radius approach)
DEFINE FIELD center ON TABLE universe_region TYPE object;
DEFINE FIELD center.x ON TABLE universe_region TYPE float DEFAULT 0.0;
DEFINE FIELD center.y ON TABLE universe_region TYPE float DEFAULT 0.0;
DEFINE FIELD center.z ON TABLE universe_region TYPE float DEFAULT 0.0;
DEFINE FIELD center.time ON TABLE universe_region TYPE float DEFAULT 0.0;
DEFINE FIELD center.physics ON TABLE universe_region TYPE float DEFAULT 0.5;
DEFINE FIELD center.biology ON TABLE universe_region TYPE float DEFAULT 0.5;
DEFINE FIELD center.logic ON TABLE universe_region TYPE float DEFAULT 0.5;
DEFINE FIELD center.quantum ON TABLE universe_region TYPE float DEFAULT 0.5;
DEFINE FIELD center.field ON TABLE universe_region TYPE float DEFAULT 0.5;
DEFINE FIELD center.control ON TABLE universe_region TYPE float DEFAULT 0.5;
DEFINE FIELD center.novelty ON TABLE universe_region TYPE float DEFAULT 0.5;
DEFINE FIELD center.precipitation ON TABLE universe_region TYPE float DEFAULT 0.5;

-- Radius for each dimension (for ellipsoidal regions)
DEFINE FIELD radius ON TABLE universe_region TYPE object;
DEFINE FIELD radius.spatial ON TABLE universe_region TYPE float DEFAULT 0.1;
DEFINE FIELD radius.temporal ON TABLE universe_region TYPE float DEFAULT 0.1;
DEFINE FIELD radius.semantic ON TABLE universe_region TYPE float DEFAULT 0.1;

-- Region metadata
DEFINE FIELD avg_coherence ON TABLE universe_region TYPE float DEFAULT 0.5;
DEFINE FIELD node_count ON TABLE universe_region TYPE int DEFAULT 0;
DEFINE FIELD created_at ON TABLE universe_region TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_region_name ON TABLE universe_region COLUMNS name UNIQUE;

-- Graph Relations

-- transition_to: Sequential state transitions
DEFINE TABLE transition_to SCHEMAFULL TYPE RELATION FROM universe_node TO universe_node;
DEFINE FIELD action ON TABLE transition_to TYPE option<string>;
DEFINE FIELD coherence_delta ON TABLE transition_to TYPE float DEFAULT 0.0;
DEFINE FIELD duration_ms ON TABLE transition_to TYPE float DEFAULT 0.0;
DEFINE FIELD created_at ON TABLE transition_to TYPE datetime DEFAULT time::now();

-- influences: Causal influence between nodes
DEFINE TABLE influences SCHEMAFULL TYPE RELATION FROM universe_node TO universe_node;
DEFINE FIELD strength ON TABLE influences TYPE float DEFAULT 0.5
    ASSERT strength >= 0.0 AND strength <= 1.0;
DEFINE FIELD influence_type ON TABLE influences TYPE string DEFAULT "causal";
DEFINE FIELD created_at ON TABLE influences TYPE datetime DEFAULT time::now();

-- similar_to: Semantic similarity between nodes
DEFINE TABLE similar_to SCHEMAFULL TYPE RELATION FROM universe_node TO universe_node;
DEFINE FIELD similarity_score ON TABLE similar_to TYPE float DEFAULT 0.0
    ASSERT similarity_score >= 0.0 AND similarity_score <= 1.0;
DEFINE FIELD created_at ON TABLE similar_to TYPE datetime DEFAULT time::now();

-- located_in: Node-region membership
DEFINE TABLE located_in SCHEMAFULL TYPE RELATION FROM universe_node TO universe_region;
DEFINE FIELD membership_strength ON TABLE located_in TYPE float DEFAULT 1.0
    ASSERT membership_strength >= 0.0 AND membership_strength <= 1.0;
DEFINE FIELD created_at ON TABLE located_in TYPE datetime DEFAULT time::now();

-- adjacent_to: Region adjacency
DEFINE TABLE adjacent_to SCHEMAFULL TYPE RELATION FROM universe_region TO universe_region;
DEFINE FIELD boundary_distance ON TABLE adjacent_to TYPE float DEFAULT 0.0;
DEFINE FIELD created_at ON TABLE adjacent_to TYPE datetime DEFAULT time::now();

-- Indexes for graph traversals
DEFINE INDEX idx_transition_in ON TABLE transition_to COLUMNS in;
DEFINE INDEX idx_transition_out ON TABLE transition_to COLUMNS out;
DEFINE INDEX idx_influences_in ON TABLE influences COLUMNS in;
DEFINE INDEX idx_influences_out ON TABLE influences COLUMNS out;
DEFINE INDEX idx_similar_in ON TABLE similar_to COLUMNS in;
DEFINE INDEX idx_similar_out ON TABLE similar_to COLUMNS out;
DEFINE INDEX idx_located_in_node ON TABLE located_in COLUMNS in;
DEFINE INDEX idx_located_in_region ON TABLE located_in COLUMNS out;