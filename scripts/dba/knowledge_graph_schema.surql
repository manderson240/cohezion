-- Traces: [KG-2] Bi-temporal upgrade (Session 96b, 2026-04-10)
-- SurrealDB 3.0 Schema: Knowledge Graph — Neurons & Synapses
--
-- Neurons: knowledge nodes sourced from Obsidian vault markdown files
-- Synapses: directed edges between neurons (latent, dream, or direct link types)
--
-- Database: cohezion:vault  (NOT cohezion:genesis — separate persistence graph)
-- Populated by: tools/vault-keeper-cycle.py via SurrealDBSync.bulk_import_concepts()
-- Graph HIHO target: 0.5 ± 0.15 (see cohezion-maintenance-mcp graph_health tool)
--
-- BI-TEMPORAL MODEL (Graphiti pattern, arXiv:2501.13956):
--   valid_from/valid_to = when the fact is true in the knowledge domain
--   SurrealKV VERSION clause = when the record was stored (system-time, automatic)
--   Combined: "what did we know at time T about state at time T'?"

-- ─────────────────────────────────────────────────────────────────
-- NEURONS (knowledge nodes)
-- ─────────────────────────────────────────────────────────────────
DEFINE TABLE neurons SCHEMAFULL;
DEFINE FIELD title      ON neurons TYPE string;
DEFINE FIELD path       ON neurons TYPE string;
DEFINE FIELD tags       ON neurons TYPE array<string>;
DEFINE FIELD tags[*]    ON neurons TYPE string;
DEFINE FIELD content    ON neurons TYPE string DEFAULT '';
DEFINE FIELD cluster_id ON neurons TYPE string DEFAULT '';
DEFINE FIELD activation ON neurons TYPE float DEFAULT 0.0;
DEFINE FIELD stage      ON neurons TYPE string DEFAULT 'active';
DEFINE FIELD created_at ON neurons TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON neurons TYPE option<datetime>;

-- Bi-temporal: valid-time (when knowledge is true in the domain)
DEFINE FIELD valid_from ON neurons TYPE datetime DEFAULT time::now();
DEFINE FIELD valid_to   ON neurons TYPE option<datetime>;

-- Embedding for vector search (GraphRAG unified queries)
DEFINE FIELD embedding ON neurons TYPE option<array<float>>;

-- Indexes
DEFINE INDEX neurons_path      ON neurons FIELDS path UNIQUE;
DEFINE INDEX neurons_cluster   ON neurons FIELDS cluster_id;
DEFINE INDEX neurons_temporal  ON neurons FIELDS valid_from, valid_to;
DEFINE INDEX neurons_embedding ON neurons FIELDS embedding HNSW DIMENSION 768 DIST COSINE TYPE F32 EFC 150 M 12;

-- ─────────────────────────────────────────────────────────────────
-- SYNAPSES (directed edges between knowledge nodes)
-- ─────────────────────────────────────────────────────────────────
DEFINE TABLE synapses SCHEMAFULL;
DEFINE FIELD source        ON synapses TYPE string;
DEFINE FIELD target        ON synapses TYPE string;
DEFINE FIELD link_type     ON synapses TYPE string;  -- latent | dream | direct
DEFINE FIELD reason        ON synapses TYPE string DEFAULT '';
DEFINE FIELD resonance     ON synapses TYPE string DEFAULT '';
DEFINE FIELD quality_score ON synapses TYPE float DEFAULT 0.0;
DEFINE FIELD similarity    ON synapses TYPE float DEFAULT 0.0;
DEFINE FIELD created_at    ON synapses TYPE datetime DEFAULT time::now();

-- Bi-temporal: valid-time windows (Graphiti pattern)
-- NULL valid_to means the relationship is still active
DEFINE FIELD valid_from ON synapses TYPE datetime DEFAULT time::now();
DEFINE FIELD valid_to   ON synapses TYPE option<datetime>;

-- Bidirectional record references (SurrealDB 3.0)
-- Enables <~ tilde reverse lookups without explicit backlinks
DEFINE FIELD source_neuron ON synapses TYPE option<record<neurons>> REFERENCE;
DEFINE FIELD target_neuron ON synapses TYPE option<record<neurons>> REFERENCE;

-- Indexes
DEFINE INDEX synapses_pair     ON synapses FIELDS source, target;
DEFINE INDEX synapses_source   ON synapses FIELDS source;
DEFINE INDEX synapses_target   ON synapses FIELDS target;
DEFINE INDEX synapses_temporal ON synapses FIELDS valid_from, valid_to;
