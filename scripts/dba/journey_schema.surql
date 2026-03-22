-- SurrealDB 3.0 Schema: Agentic Journey Tracking
-- Tracks agent actions through the 12D coherence universe

-- agent_journey: Complete journey record for an agent session
-- Captures the full trajectory through the 12D universe
DEFINE TABLE agent_journey SCHEMAFULL;

DEFINE FIELD journey_id ON TABLE agent_journey TYPE string;
DEFINE FIELD agent_id ON TABLE agent_journey TYPE string;
DEFINE FIELD agent_name ON TABLE agent_journey TYPE string;
DEFINE FIELD intent ON TABLE agent_journey TYPE string;

-- Temporal tracking
DEFINE FIELD started_at ON TABLE agent_journey TYPE datetime DEFAULT time::now();
DEFINE FIELD completed_at ON TABLE agent_journey TYPE option<datetime>;

-- Status: active, completed, failed, checkpointed
DEFINE FIELD status ON TABLE agent_journey TYPE string DEFAULT "active"
    ASSERT status IN ["active", "completed", "failed", "checkpointed"];

-- Final metrics
DEFINE FIELD final_coherence ON TABLE agent_journey TYPE float DEFAULT 0.0
    ASSERT final_coherence >= 0.0 AND final_coherence <= 1.0;
DEFINE FIELD final_phi_score ON TABLE agent_journey TYPE float DEFAULT 0.0
    ASSERT final_phi_score >= 0.0 AND final_phi_score <= 1.0;

-- Aggregation fields
DEFINE FIELD total_steps ON TABLE agent_journey TYPE int DEFAULT 0;
DEFINE FIELD total_duration_ms ON TABLE agent_journey TYPE float DEFAULT 0.0;

-- 12D physics state (final position in universe)
DEFINE FIELD physics_state ON TABLE agent_journey TYPE object;
DEFINE FIELD physics_state.x ON TABLE agent_journey TYPE float DEFAULT 0.0;
DEFINE FIELD physics_state.y ON TABLE agent_journey TYPE float DEFAULT 0.0;
DEFINE FIELD physics_state.z ON TABLE agent_journey TYPE float DEFAULT 0.0;
DEFINE FIELD physics_state.time ON TABLE agent_journey TYPE float DEFAULT 0.0;
DEFINE FIELD physics_state.physics ON TABLE agent_journey TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.biology ON TABLE agent_journey TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.logic ON TABLE agent_journey TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.quantum ON TABLE agent_journey TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.field ON TABLE agent_journey TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.control ON TABLE agent_journey TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.novelty ON TABLE agent_journey TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.precipitation ON TABLE agent_journey TYPE float DEFAULT 0.5;

-- Trajectory history for plotting coherence/efficiency over time
DEFINE FIELD coherence_trajectory ON TABLE agent_journey TYPE array<float>;
DEFINE FIELD coherence_trajectory[*] ON TABLE agent_journey TYPE float;
DEFINE FIELD efficiency_trajectory ON TABLE agent_journey TYPE array<float>;
DEFINE FIELD efficiency_trajectory[*] ON TABLE agent_journey TYPE float;

-- Flexible metadata for extensible data
DEFINE FIELD metadata ON TABLE agent_journey TYPE object;

-- Indexes for common queries
DEFINE INDEX idx_journey_journey_id ON TABLE agent_journey COLUMNS journey_id;
DEFINE INDEX idx_journey_agent_id ON TABLE agent_journey COLUMNS agent_id;
DEFINE INDEX idx_journey_status ON TABLE agent_journey COLUMNS status;
DEFINE INDEX idx_journey_started_at ON TABLE agent_journey COLUMNS started_at;

-- journey_point: Individual point in an agent's journey
-- Records each step/action in the 12D universe
DEFINE TABLE journey_point SCHEMAFULL;

DEFINE FIELD journey ON TABLE journey_point TYPE record<agent_journey>;
DEFINE FIELD agent_id ON TABLE journey_point TYPE string;
DEFINE FIELD timestamp ON TABLE journey_point TYPE datetime DEFAULT time::now();

-- Phase: planning, execution, reflection, refinement
DEFINE FIELD phase ON TABLE journey_point TYPE string DEFAULT "execution"
    ASSERT phase IN ["planning", "execution", "reflection", "refinement", "checkpoint"];

-- Metrics at this point
DEFINE FIELD coherence ON TABLE journey_point TYPE float DEFAULT 0.5
    ASSERT coherence >= 0.0 AND coherence <= 1.0;
DEFINE FIELD efficiency ON TABLE journey_point TYPE float DEFAULT 0.5
    ASSERT efficiency >= 0.0 AND efficiency <= 1.0;

-- 12D physics state at this point
DEFINE FIELD physics_state ON TABLE journey_point TYPE object;
DEFINE FIELD physics_state.x ON TABLE journey_point TYPE float DEFAULT 0.0;
DEFINE FIELD physics_state.y ON TABLE journey_point TYPE float DEFAULT 0.0;
DEFINE FIELD physics_state.z ON TABLE journey_point TYPE float DEFAULT 0.0;
DEFINE FIELD physics_state.time ON TABLE journey_point TYPE float DEFAULT 0.0;
DEFINE FIELD physics_state.physics ON TABLE journey_point TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.biology ON TABLE journey_point TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.logic ON TABLE journey_point TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.quantum ON TABLE journey_point TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.field ON TABLE journey_point TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.control ON TABLE journey_point TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.novelty ON TABLE journey_point TYPE float DEFAULT 0.5;
DEFINE FIELD physics_state.precipitation ON TABLE journey_point TYPE float DEFAULT 0.5;

-- Action details
DEFINE FIELD action ON TABLE journey_point TYPE string;
DEFINE FIELD result ON TABLE journey_point TYPE option<string>;
DEFINE FIELD duration_ms ON TABLE journey_point TYPE float DEFAULT 0.0;

-- Skill and model tracking
DEFINE FIELD skill_used ON TABLE journey_point TYPE option<string>;
DEFINE FIELD model_used ON TABLE journey_point TYPE option<string>;

-- Flexible metadata
DEFINE FIELD metadata ON TABLE journey_point TYPE object;

-- Indexes
DEFINE INDEX idx_point_journey ON TABLE journey_point COLUMNS journey;
DEFINE INDEX idx_point_agent_id ON TABLE journey_point COLUMNS agent_id;
DEFINE INDEX idx_point_timestamp ON TABLE journey_point COLUMNS timestamp;
DEFINE INDEX idx_point_phase ON TABLE journey_point COLUMNS phase;

-- journey_knowledge: Extracted knowledge from completed journeys
-- Stores patterns, anti-patterns, insights for learning
DEFINE TABLE journey_knowledge SCHEMAFULL;

DEFINE FIELD source_journey ON TABLE journey_knowledge TYPE option<record<agent_journey>>;

-- knowledge_type: pattern, anti_pattern, insight, skill_refinement
DEFINE FIELD knowledge_type ON TABLE journey_knowledge TYPE string
    ASSERT knowledge_type IN ["pattern", "anti_pattern", "insight", "skill_refinement"];

DEFINE FIELD content ON TABLE journey_knowledge TYPE string;
DEFINE FIELD confidence ON TABLE journey_knowledge TYPE float DEFAULT 0.5
    ASSERT confidence >= 0.0 AND confidence <= 1.0;

-- Vector embedding for semantic search
DEFINE FIELD embedding ON TABLE journey_knowledge TYPE option<array<float>>;
DEFINE FIELD embedding[*] ON TABLE journey_knowledge TYPE float;

DEFINE FIELD created_at ON TABLE journey_knowledge TYPE datetime DEFAULT time::now();
DEFINE FIELD validated ON TABLE journey_knowledge TYPE bool DEFAULT false;

-- Indexes
DEFINE INDEX idx_knowledge_type ON TABLE journey_knowledge COLUMNS knowledge_type;
DEFINE INDEX idx_knowledge_validated ON TABLE journey_knowledge COLUMNS validated;
DEFINE INDEX idx_knowledge_created_at ON TABLE journey_knowledge COLUMNS created_at;

-- HNSW index for vector similarity (768 dim)
DEFINE INDEX idx_knowledge_embedding ON TABLE journey_knowledge
    COLUMNS embedding
    HNSW DIMENSION 768 DIST COSINE TYPE F32 EFC 150 M 12;

-- Graph relations for journey connections
DEFINE TABLE led_to SCHEMAFULL TYPE RELATION FROM journey_point TO journey_point;
DEFINE FIELD transition_type ON TABLE led_to TYPE string DEFAULT "sequential";
DEFINE FIELD coherence_delta ON TABLE led_to TYPE float DEFAULT 0.0;

DEFINE TABLE informed_by SCHEMAFULL TYPE RELATION FROM journey_knowledge TO journey_knowledge;
DEFINE FIELD relevance ON TABLE informed_by TYPE float DEFAULT 0.5;

DEFINE TABLE derived_from SCHEMAFULL TYPE RELATION FROM journey_knowledge TO agent_journey;
DEFINE FIELD extraction_confidence ON TABLE derived_from TYPE float DEFAULT 0.5;