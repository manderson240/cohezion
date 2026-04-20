# SurrealDB Schema: Code Patterns and Anti-Patterns

# Information about a detected code pattern
DEFINE TABLE code_patterns SCHEMALESS;
DEFINE FIELD name ON TABLE code_patterns TYPE string;
DEFINE FIELD category ON TABLE code_patterns TYPE string;
DEFINE FIELD description ON TABLE code_patterns TYPE string;
DEFINE FIELD file_paths ON TABLE code_patterns TYPE array<string>;
DEFINE FIELD code_example ON TABLE code_patterns TYPE string;
DEFINE FIELD frequency ON TABLE code_patterns TYPE int DEFAULT 1;
DEFINE FIELD confidence ON TABLE code_patterns TYPE float;
DEFINE FIELD first_seen ON TABLE code_patterns TYPE datetime DEFAULT time::now();
DEFINE FIELD last_seen ON TABLE code_patterns TYPE datetime DEFAULT time::now();
DEFINE FIELD obsidian_synced ON TABLE code_patterns TYPE bool DEFAULT false;
DEFINE FIELD sync_status ON TABLE code_patterns TYPE string DEFAULT "pending";
DEFINE FIELD metadata ON TABLE code_patterns FLEXIBLE TYPE object;

# HNSW Index for vector similarity search (768 dimensions for nomic-embed-text)
DEFINE FIELD embedding ON TABLE code_patterns FLEXIBLE TYPE option<array<float>> HNSW DIMENSION 768 DIST COSINE TYPE F32;

# Information about a detected code anti-pattern
DEFINE TABLE code_anti_patterns SCHEMALESS;
DEFINE FIELD name ON TABLE code_anti_patterns TYPE string;
DEFINE FIELD category ON TABLE code_anti_patterns TYPE string;
DEFINE FIELD description ON TABLE code_anti_patterns TYPE string;
DEFINE FIELD file_paths ON TABLE code_anti_patterns TYPE array<string>;
DEFINE FIELD severity ON TABLE code_anti_patterns TYPE string; # low, medium, high, critical
DEFINE FIELD risk_level ON TABLE code_anti_patterns TYPE int; # 1-10
DEFINE FIELD remediation ON TABLE code_anti_patterns TYPE string;
DEFINE FIELD code_example ON TABLE code_anti_patterns TYPE string;
DEFINE FIELD frequency ON TABLE code_anti_patterns TYPE int DEFAULT 1;
DEFINE FIELD confidence ON TABLE code_anti_patterns TYPE float;
DEFINE FIELD first_seen ON TABLE code_anti_patterns TYPE datetime DEFAULT time::now();
DEFINE FIELD last_seen ON TABLE code_anti_patterns TYPE datetime DEFAULT time::now();
DEFINE FIELD obsidian_synced ON TABLE code_anti_patterns TYPE bool DEFAULT false;
DEFINE FIELD sync_status ON TABLE code_anti_patterns TYPE string DEFAULT "pending";
DEFINE FIELD metadata ON TABLE code_anti_patterns FLEXIBLE TYPE object;

# HNSW Index for anti-patterns
DEFINE FIELD embedding ON TABLE code_anti_patterns FLEXIBLE TYPE option<array<float>> HNSW DIMENSION 768 DIST COSINE TYPE F32;

# Edge table for relationships between patterns
DEFINE TABLE pattern_relates_to SCHEMALESS;
DEFINE FIELD relation_type ON TABLE pattern_relates_to TYPE string;
DEFINE FIELD weight ON TABLE pattern_relates_to TYPE float DEFAULT 1.0;
