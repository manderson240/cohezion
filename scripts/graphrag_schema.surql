-- GraphRAG Schema for Cohezion Vault Knowledge
-- Combines vector similarity with graph relationships

-- Use cohezion namespace and vault database
USE NS cohezion DB vault;

-- VAULT MEMORY: Documents with embeddings
DEFINE TABLE vault_memory SCHEMAFUL;
DEFINE FIELD type ON vault_memory TYPE string
    ASSERT $value INSIDE ['decision', 'pattern', 'experiment'];
DEFINE FIELD path ON vault_memory TYPE string;
DEFINE FIELD title ON vault_memory TYPE string;
DEFINE FIELD content ON vault_memory TYPE string;
DEFINE FIELD embedding ON vault_memory TYPE option<array<float>>;
DEFINE FIELD created_at ON vault_memory TYPE datetime DEFAULT time::now();
DEFINE FIELD tags ON vault_memory TYPE array<string> DEFAULT [];

-- Vector search index (768-dim for nomic-embed-text)
DEFINE INDEX idx_vector ON vault_memory FIELDS embedding
    MTREE DIMENSION 768 DIST COSINE;

-- GRAPH EDGES: Relational context
DEFINE TABLE led_to SCHEMAFUL TYPE RELATION
    IN vault_memory OUT vault_memory;
DEFINE FIELD reason ON led_to TYPE string;
DEFINE FIELD created_at ON led_to TYPE datetime DEFAULT time::now();

DEFINE TABLE informed_by SCHEMAFUL TYPE RELATION
    IN vault_memory OUT vault_memory;
DEFINE FIELD how ON informed_by TYPE string;

DEFINE TABLE used_in SCHEMAFUL TYPE RELATION
    IN vault_memory OUT vault_memory;
DEFINE FIELD context ON used_in TYPE string;

DEFINE TABLE extracted_from SCHEMAFUL TYPE RELATION
    IN vault_memory OUT vault_memory;
DEFINE FIELD session ON extracted_from TYPE string;

-- AGENT REGISTRY: Cohezion agents with capabilities
DEFINE TABLE cohezion_agent SCHEMAFUL;
DEFINE FIELD name ON cohezion_agent TYPE string;
DEFINE FIELD agent_type ON cohezion_agent TYPE string;
DEFINE FIELD capabilities ON cohezion_agent TYPE array<string> DEFAULT [];
DEFINE FIELD coherence_history ON cohezion_agent TYPE array<float> DEFAULT [];
DEFINE FIELD cost_tier ON cohezion_agent TYPE string DEFAULT 'free'
    ASSERT $value INSIDE ['free', 'paid', 'premium'];
DEFINE FIELD created_at ON cohezion_agent TYPE datetime DEFAULT time::now();

-- TASK ORCHESTRATION: Event-driven task queue
DEFINE TABLE cohezion_task SCHEMAFUL;
DEFINE FIELD objective ON cohezion_task TYPE string;
DEFINE FIELD status ON cohezion_task TYPE string DEFAULT 'pending'
    ASSERT $value INSIDE ['pending', 'in_progress', 'completed', 'failed'];
DEFINE FIELD assigned_to ON cohezion_task TYPE option<record<cohezion_agent>>;
DEFINE FIELD required_capabilities ON cohezion_task TYPE array<string> DEFAULT [];
DEFINE FIELD priority ON cohezion_task TYPE int DEFAULT 5;
DEFINE FIELD created_at ON cohezion_task TYPE datetime DEFAULT time::now();
DEFINE FIELD completed_at ON cohezion_task TYPE option<datetime>;

-- Index for fast task queries
DEFINE INDEX idx_task_status ON cohezion_task FIELDS status;
