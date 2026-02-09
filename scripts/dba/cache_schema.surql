DEFINE TABLE semantic_cache SCHEMAFULL;
DEFINE FIELD query_text ON semantic_cache TYPE string PERMISSIONS FULL;
DEFINE FIELD response_content ON semantic_cache TYPE string PERMISSIONS FULL;
DEFINE FIELD embedding ON semantic_cache TYPE array<float> PERMISSIONS FULL;
DEFINE FIELD embedding[*] ON semantic_cache TYPE float PERMISSIONS FULL;
DEFINE FIELD created_at ON semantic_cache TYPE datetime DEFAULT time::now() PERMISSIONS FULL;

-- HNSW Index for Vector Search (768 dimensions for nomic-embed-text)
DEFINE INDEX idx_cache_embedding ON semantic_cache FIELDS embedding HNSW DIMENSION 768 DIST COSINE TYPE F32 EFC 150 M 12 M0 24 LM 0.40;
