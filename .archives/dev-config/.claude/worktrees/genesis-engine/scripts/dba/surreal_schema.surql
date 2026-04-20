-- Define the table
DEFINE TABLE universe_nodes SCHEMALESS;

-- Define fields (optional, but good for structure)
DEFINE FIELD id ON TABLE universe_nodes TYPE record;
DEFINE FIELD type ON TABLE universe_nodes FLEXIBLE TYPE option<string>;
-- Content might be missing in metadata nodes, so make it optional/any
DEFINE FIELD content ON TABLE universe_nodes FLEXIBLE TYPE option<string>;
DEFINE FIELD timestamp ON TABLE universe_nodes FLEXIBLE TYPE option<datetime> DEFAULT time::now();
DEFINE FIELD embedding ON TABLE universe_nodes FLEXIBLE TYPE option<array<float>>;

-- Indexes for performance
-- Type lookup is frequent
DEFINE INDEX idx_type ON TABLE universe_nodes COLUMNS type;

-- Timestamp for time-travel queries
DEFINE INDEX idx_timestamp ON TABLE universe_nodes COLUMNS timestamp;

-- HNSW Index for Vector Search (1536 dim for OpenAI, or 768 for local)
-- Assuming 768 for now based on local models, or 1536 if OpenAI. 
-- Let's use flexible dimension or specific if known. 
-- The user has "Local Ollama Roster" and "Gemini", so likely mixed.
-- We'll define it for MRL (Matryoshka Representation Learning) if possible, or standard HNSW.
-- MRL isn't native yet, standard HNSW:
DEFINE INDEX idx_embedding ON TABLE universe_nodes COLUMNS embedding HNSW DIMENSION 768 DIST COSINE TYPE F32;

-- Graph Edges (if we want explicit edge table)
DEFINE TABLE connected_to SCHEMALESS;
DEFINE FIELD in ON TABLE connected_to TYPE record<universe_nodes>;
DEFINE FIELD out ON TABLE connected_to TYPE record<universe_nodes>;
DEFINE INDEX idx_in ON TABLE connected_to COLUMNS in;
DEFINE INDEX idx_out ON TABLE connected_to COLUMNS out;
