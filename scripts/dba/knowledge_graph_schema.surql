-- Traces: [KG-1]
-- SurrealDB 3.0 Schema: Knowledge Graph — Neurons & Synapses
--
-- Neurons: knowledge nodes sourced from Obsidian vault markdown files
-- Synapses: directed edges between neurons (latent, dream, or direct link types)
--
-- Database: cohezion:vault  (NOT cohezion:genesis — separate persistence graph)
-- Populated by: tools/vault-keeper-cycle.py via SurrealDBSync.bulk_import_concepts()
-- Graph HIHO target: 0.5 ± 0.15 (see cohezion-maintenance-mcp graph_health tool)

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

DEFINE INDEX neurons_path    ON neurons FIELDS path UNIQUE;
DEFINE INDEX neurons_cluster ON neurons FIELDS cluster_id;

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

DEFINE INDEX synapses_pair   ON synapses FIELDS source, target;
DEFINE INDEX synapses_source ON synapses FIELDS source;
DEFINE INDEX synapses_target ON synapses FIELDS target;
