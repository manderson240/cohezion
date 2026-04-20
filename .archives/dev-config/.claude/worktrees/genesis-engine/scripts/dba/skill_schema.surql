-- SurrealDB 3.0 Schema: Skill Registry
-- Manages PRIME skill definitions with semantic search capabilities

-- skill: Registry of available skills with embeddings for semantic lookup
DEFINE TABLE skill SCHEMAFULL;

DEFINE FIELD name ON TABLE skill TYPE string
    ASSERT string::len(name) > 0 AND string::len(name) <= 100;
DEFINE FIELD description ON TABLE skill TYPE string;
DEFINE FIELD path ON TABLE skill TYPE string;

-- Versioning
DEFINE FIELD version ON TABLE skill TYPE string DEFAULT "0.1.0";

-- Categorization
DEFINE FIELD keywords ON TABLE skill TYPE array<string>;
DEFINE FIELD keywords[*] ON TABLE skill TYPE string;
DEFINE FIELD category ON TABLE skill TYPE string DEFAULT "general";

-- Activation state
DEFINE FIELD active ON TABLE skill TYPE bool DEFAULT true;

-- Performance metrics
DEFINE FIELD success_rate ON TABLE skill TYPE float DEFAULT 0.0
    ASSERT success_rate >= 0.0 AND success_rate <= 1.0;
DEFINE FIELD invocation_count ON TABLE skill TYPE int DEFAULT 0;
DEFINE FIELD last_invoked ON TABLE skill TYPE option<datetime>;

-- Flexible metadata for skill-specific data
DEFINE FIELD metadata ON TABLE skill TYPE object;

-- Vector embedding for semantic skill matching
DEFINE FIELD embedding ON TABLE skill TYPE option<array<float>>;
DEFINE FIELD embedding[*] ON TABLE skill TYPE float;

-- Timestamps
DEFINE FIELD created_at ON TABLE skill TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE skill TYPE datetime DEFAULT time::now();

-- Indexes
DEFINE INDEX idx_skill_name ON TABLE skill COLUMNS name UNIQUE;
DEFINE INDEX idx_skill_category ON TABLE skill COLUMNS category;
DEFINE INDEX idx_skill_active ON TABLE skill COLUMNS active;
DEFINE INDEX idx_skill_last_invoked ON TABLE skill COLUMNS last_invoked;

-- HNSW index for semantic skill search (768 dim)
DEFINE INDEX idx_skill_embedding ON TABLE skill
    COLUMNS embedding
    HNSW DIMENSION 768 DIST COSINE TYPE F32 EFC 150 M 12;

-- skill_invocation: Log of skill invocations for analytics
DEFINE TABLE skill_invocation SCHEMAFULL;

DEFINE FIELD skill ON TABLE skill_invocation TYPE record<skill>;
DEFINE FIELD invoked_at ON TABLE skill_invocation TYPE datetime DEFAULT time::now();
DEFINE FIELD agent_id ON TABLE skill_invocation TYPE string;
DEFINE FIELD journey_id ON TABLE skill_invocation TYPE option<string>;

-- Invocation context
DEFINE FIELD input_summary ON TABLE skill_invocation TYPE option<string>;
DEFINE FIELD output_summary ON TABLE skill_invocation TYPE option<string>;
DEFINE FIELD success ON TABLE skill_invocation TYPE bool DEFAULT true;
DEFINE FIELD duration_ms ON TABLE skill_invocation TYPE float DEFAULT 0.0;

-- Metrics captured during invocation
DEFINE FIELD coherence_before ON TABLE skill_invocation TYPE option<float>;
DEFINE FIELD coherence_after ON TABLE skill_invocation TYPE option<float>;
DEFINE FIELD model_used ON TABLE skill_invocation TYPE option<string>;

-- Error information
DEFINE FIELD error_message ON TABLE skill_invocation TYPE option<string>;
DEFINE FIELD error_type ON TABLE skill_invocation TYPE option<string>;

-- Indexes for analytics
DEFINE INDEX idx_invocation_skill ON TABLE skill_invocation COLUMNS skill;
DEFINE INDEX idx_invocation_invoked_at ON TABLE skill_invocation COLUMNS invoked_at;
DEFINE INDEX idx_invocation_agent_id ON TABLE skill_invocation COLUMNS agent_id;
DEFINE INDEX idx_invocation_success ON TABLE skill_invocation COLUMNS success;

-- skill_dependency: Track skill dependencies
DEFINE TABLE skill_dependency SCHEMAFULL TYPE RELATION FROM skill TO skill;

DEFINE FIELD dependency_type ON TABLE skill_dependency TYPE string DEFAULT "requires"
    ASSERT dependency_type IN ["requires", "enhances", "conflicts"];
DEFINE FIELD optional ON TABLE skill_dependency TYPE bool DEFAULT false;

-- skill_tag: Lightweight tagging for skill categorization
DEFINE TABLE skill_tag SCHEMAFULL;

DEFINE FIELD skill ON TABLE skill_tag TYPE record<skill>;
DEFINE FIELD tag ON TABLE skill_tag TYPE string;
DEFINE FIELD created_at ON TABLE skill_tag TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_skill_tag_skill ON TABLE skill_tag COLUMNS skill;
DEFINE INDEX idx_skill_tag_tag ON TABLE skill_tag COLUMNS tag;