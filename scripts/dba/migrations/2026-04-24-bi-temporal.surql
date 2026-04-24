-- Migration: bi-temporal columns on universe_node and agent_journey.
--
-- Adds valid_from, valid_to, transaction_time to enable point-in-time queries.
-- This mirrors the bi-temporal columns already present on precipitation_event
-- and brings the three core universe-state tables into line with the
-- precipitation event contract.
--
-- valid_from / valid_to: when the fact was true in the universe being modeled.
-- transaction_time: when the fact was recorded in our system.
--
-- See precipitation_schema.surql for the pattern this extends.

-- universe_node: add bi-temporal columns.
DEFINE FIELD valid_from       ON universe_node TYPE datetime DEFAULT time::now();
DEFINE FIELD valid_to         ON universe_node TYPE option<datetime>;
DEFINE FIELD transaction_time ON universe_node TYPE datetime DEFAULT time::now();

-- agent_journey: add bi-temporal columns (started_at already exists as the
-- journey's universe-time start; we add valid_to and transaction_time).
DEFINE FIELD valid_to         ON agent_journey TYPE option<datetime>;
DEFINE FIELD transaction_time ON agent_journey TYPE datetime DEFAULT time::now();

-- Index to support point-in-time queries.
DEFINE INDEX idx_unode_valid_from ON TABLE universe_node COLUMNS valid_from;
DEFINE INDEX idx_journey_valid_to ON TABLE agent_journey COLUMNS valid_to;
