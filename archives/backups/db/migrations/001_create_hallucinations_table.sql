CREATE TABLE hallucinations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agent_name VARCHAR(255) NOT NULL,
    original_request TEXT,
    hallucinated_output TEXT NOT NULL,
    correction TEXT,
    notes TEXT,
    metadata JSONB
);
