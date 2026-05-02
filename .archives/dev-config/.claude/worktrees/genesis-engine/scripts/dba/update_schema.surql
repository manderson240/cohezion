-- Update fields to be optional/flexible (fixing ingestion errors)
DEFINE FIELD type ON TABLE universe_nodes FLEXIBLE TYPE option<string>;
DEFINE FIELD content ON TABLE universe_nodes FLEXIBLE TYPE option<string>;
DEFINE FIELD timestamp ON TABLE universe_nodes FLEXIBLE TYPE option<datetime> DEFAULT time::now();
DEFINE FIELD embedding ON TABLE universe_nodes FLEXIBLE TYPE option<array<float>>;

-- Ensure indexes exist
DEFINE INDEX idx_type ON TABLE universe_nodes COLUMNS type;
DEFINE INDEX idx_timestamp ON TABLE universe_nodes COLUMNS timestamp;
