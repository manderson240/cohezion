"""SurrealDB schema definitions for Universe Simulation v2.0.

This module defines the database schema for capturing every agent interaction
as 12D/512D manifold data, enabling universe simulation and experience learning.
"""

from __future__ import annotations


UNIVERSE_SCHEMA = """
-- Universe Simulation Tables

-- Core journey tracking (every task is a journey through the manifold)
DEFINE TABLE universe_journey SCHEMALESS;
DEFINE INDEX idx_journey_agent ON universe_journey FIELDS agent_name;
DEFINE INDEX idx_journey_status ON universe_journey FIELDS status;
DEFINE INDEX idx_journey_time ON universe_journey FIELDS created_at;

-- 12D Axiomatic State (the "Body" of the agent in physical space)
DEFINE TABLE axiomatic_state SCHEMALESS;
DEFINE INDEX idx_axiomatic_journey ON axiomatic_state FIELDS journey_id;
DEFINE INDEX idx_axiomatic_time ON axiomatic_state FIELDS timestamp;

-- 2048D Latent State (the "Soul" - semantic hypervolume)
DEFINE TABLE latent_state SCHEMALESS;
DEFINE INDEX idx_latent_journey ON latent_state FIELDS journey_id;
DEFINE INDEX idx_latent_vector ON latent_state FIELDS embedding
    TYPE VECTOR DIMENSION 2048 DIST COSINE;

-- Trajectory points (FLUME evolution through manifold)
DEFINE TABLE trajectory_point SCHEMALESS;
DEFINE INDEX idx_trajectory_journey ON trajectory_point FIELDS journey_id;
DEFINE INDEX idx_trajectory_step ON trajectory_point FIELDS step_number;

-- Coherence measurements (HIHO stability tracking)
DEFINE TABLE coherence_measurement SCHEMALESS;
DEFINE INDEX idx_coherence_journey ON coherence_measurement FIELDS journey_id;
DEFINE INDEX idx_coherence_value ON coherence_measurement FIELDS coherence_score;

-- Precipitated reality (manifested outputs - code, docs, actions)
DEFINE TABLE precipitation SCHEMALESS;
DEFINE INDEX idx_precipitation_journey ON precipitation FIELDS journey_id;
DEFINE INDEX idx_precipitation_type ON precipitation FIELDS type;

-- Knowledge extracted (learnings from each journey)
DEFINE TABLE knowledge_extract SCHEMALESS;
DEFINE INDEX idx_knowledge_journey ON knowledge_extract FIELDS journey_id;
DEFINE INDEX idx_knowledge_pattern ON knowledge_extract FIELDS pattern_type;
DEFINE INDEX idx_knowledge_vector ON knowledge_extract FIELDS embedding
    TYPE VECTOR DIMENSION 2048 DIST COSINE;

-- Reward ledger (XP, badges, streaks)
DEFINE TABLE reward_ledger SCHEMALESS;
DEFINE INDEX idx_reward_agent ON reward_ledger FIELDS agent_id;
DEFINE INDEX idx_reward_type ON reward_ledger FIELDS reward_type;
DEFINE INDEX idx_reward_time ON reward_ledger FIELDS awarded_at;

-- Achievement unlocks
DEFINE TABLE achievement SCHEMALESS;
DEFINE INDEX idx_achievement_agent ON achievement FIELDS agent_id;
DEFINE INDEX idx_achievement_badge ON achievement FIELDS badge_id;

-- Evolution history (self-improvement tracking)
DEFINE TABLE evolution_event SCHEMALESS;
DEFINE INDEX idx_evolution_time ON evolution_event FIELDS created_at;
DEFINE INDEX idx_evolution_type ON evolution_event FIELDS event_type;

-- Meta-programming generated artifacts
DEFINE TABLE generated_artifact SCHEMALESS;
DEFINE INDEX idx_artifact_type ON generated_artifact FIELDS artifact_type;
DEFINE INDEX idx_artifact_template ON generated_artifact FIELDS template_id;

-- Functions for HIHO coherence calculation
DEFINE FUNCTION fn::calculate_coherence($internal INTENT, $external INTENT) {
    -- Calculate 0.5 coherence (Half-In-Half-Out stability)
    RETURN vector::similarity::cosine($internal, $external);
};

-- Function to find similar journeys (experience replay)
DEFINE FUNCTION fn::find_similar_journeys($query_vector ARRAY, $threshold FLOAT) {
    RETURN SELECT * FROM latent_state
    WHERE embedding <|8|> $query_vector
    AND vector::similarity::cosine(embedding, $query_vector) > $threshold;
};
"""

# Migration scripts for each table
MIGRATIONS = {
    "001_universe_journey": """
        DEFINE TABLE universe_journey SCHEMALESS;
        DEFINE INDEX idx_journey_agent ON universe_journey FIELDS agent_name;
        DEFINE INDEX idx_journey_status ON universe_journey FIELDS status;
        DEFINE INDEX idx_journey_time ON universe_journey FIELDS created_at;
    """,
    "002_axiomatic_state": """
        DEFINE TABLE axiomatic_state SCHEMALESS;
        DEFINE INDEX idx_axiomatic_journey ON axiomatic_state FIELDS journey_id;
        DEFINE INDEX idx_axiomatic_time ON axiomatic_state FIELDS timestamp;
    """,
    "003_latent_state": """
        DEFINE TABLE latent_state SCHEMALESS;
        DEFINE INDEX idx_latent_journey ON latent_state FIELDS journey_id;
        DEFINE INDEX idx_latent_vector ON latent_state FIELDS embedding
    TYPE VECTOR DIMENSION 2048 DIST COSINE;
    """,
    "004_trajectory": """
        DEFINE TABLE trajectory_point SCHEMALESS;
        DEFINE INDEX idx_trajectory_journey ON trajectory_point FIELDS journey_id;
        DEFINE INDEX idx_trajectory_step ON trajectory_point FIELDS step_number;
    """,
    "005_coherence": """
        DEFINE TABLE coherence_measurement SCHEMALESS;
        DEFINE INDEX idx_coherence_journey ON coherence_measurement FIELDS journey_id;
        DEFINE INDEX idx_coherence_value ON coherence_measurement FIELDS coherence_score;
    """,
    "006_precipitation": """
        DEFINE TABLE precipitation SCHEMALESS;
        DEFINE INDEX idx_precipitation_journey ON precipitation FIELDS journey_id;
        DEFINE INDEX idx_precipitation_type ON precipitation FIELDS type;
    """,
    "007_knowledge": """
        DEFINE TABLE knowledge_extract SCHEMALESS;
        DEFINE INDEX idx_knowledge_journey ON knowledge_extract FIELDS journey_id;
        DEFINE INDEX idx_knowledge_pattern ON knowledge_extract FIELDS pattern_type;
        DEFINE INDEX idx_knowledge_vector ON knowledge_extract FIELDS embedding
            TYPE VECTOR DIMENSION 512 DIST COSINE;
    """,
    "008_rewards": """
        DEFINE TABLE reward_ledger SCHEMALESS;
        DEFINE INDEX idx_reward_agent ON reward_ledger FIELDS agent_id;
        DEFINE INDEX idx_reward_type ON reward_ledger FIELDS reward_type;
        DEFINE INDEX idx_reward_time ON reward_ledger FIELDS awarded_at;
    """,
    "009_achievements": """
        DEFINE TABLE achievement SCHEMALESS;
        DEFINE INDEX idx_achievement_agent ON achievement FIELDS agent_id;
        DEFINE INDEX idx_achievement_badge ON achievement FIELDS badge_id;
    """,
    "010_evolution": """
        DEFINE TABLE evolution_event SCHEMALESS;
        DEFINE INDEX idx_evolution_time ON evolution_event FIELDS created_at;
        DEFINE INDEX idx_evolution_type ON evolution_event FIELDS event_type;
    """,
}

# Local storage fallback schema (SQLite for offline mode)
LOCAL_SCHEMA = """
-- Local SQLite fallback when SurrealDB unavailable

CREATE TABLE IF NOT EXISTS universe_journey (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    intent TEXT,
    status TEXT DEFAULT 'active',
    coherence_target REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata TEXT -- JSON blob
);

CREATE TABLE IF NOT EXISTS axiomatic_state (
    id TEXT PRIMARY KEY,
    journey_id TEXT REFERENCES universe_journey(id),
    spatial_x REAL, spatial_y REAL, spatial_z REAL, temporal REAL,
    physics REAL, biology REAL, logic REAL, quantum REAL,
    field REAL, control REAL, novelty REAL, precipitation REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS latent_state (
    id TEXT PRIMARY KEY,
    journey_id TEXT REFERENCES universe_journey(id),
    embedding TEXT, -- JSON array of 512 floats
    semantic_intent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reward_ledger (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    reward_type TEXT NOT NULL,
    amount INTEGER NOT NULL,
    badge_id TEXT,
    description TEXT,
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS achievement (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    badge_id TEXT NOT NULL,
    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rarity TEXT DEFAULT 'common'
);

CREATE INDEX IF NOT EXISTS idx_journey_agent ON universe_journey(agent_name);
CREATE INDEX IF NOT EXISTS idx_journey_status ON universe_journey(status);
CREATE INDEX IF NOT EXISTS idx_reward_agent ON reward_ledger(agent_id);
"""
