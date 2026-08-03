# data_mesh — Local Context

This file loads in addition to the root `CLAUDE.md`. Root applies here too.

**Purpose:** Data Mesh architecture for Cohezion's multi-agent system. Maps Zhamak Dehghani's 4 Data Mesh principles to Cohezion: 1. Domain ownership → Each specialist agent owns its data domain 2. Data as product

## Entry points (14 modules)

| Module | Key class(es) | LOC |
|---|---|---|
| `audio_telemetry.py` | `TaxonomyLevel`, `BirdSpeciesNode`, `AudioSegmentMetadata` | 80 |
| `corpus_quality_consumer.py` | `CorpusQualityConsumer` | 142 |
| `data_product.py` | `DataProductStatus`, `DataQualityTier`, `DataProductSchema` | 259 |
| `event_bridge.py` | `DataMeshEventBridge` | 289 |
| `event_consumer.py` | `EventConsumer` | 216 |
| `gaia_domain_agent.py` | `GaiaDataAgent` | 215 |
| `gaia_agent_roster.py` | `ModelSelector`, `AgentSpec`, `GaiaAgentRoster` | 249 |
| `inference_products.py` | _(functions)_ `build_inference_products`, `get_product_for_capability` | 245 |
| `journey_telemetry.py` | `HardwareTier`, `SwarmExpert`, `QuadratureFabrics` | 93 |
| `kanban_bridge.py` | _(functions)_ `persist_item`, `backfill_items` | 160 |
| `land_runner.py` | `LandVerdict` | 231 |
| `lemonade_multimodal.py` | `LemonadeMultimodalClient` | 142 |
| `research_products.py` | `ResearchFinding` | 495 |
| `universe_telemetry.py` | `UniverseStateEvent` | 52 |

## Invariants / notes referencing this package (from harness.md / root CLAUDE.md)

- | `src/cohezion/data_mesh/data_product.py` | **DATA MESH** | Typed data products with SLA for 17+ MCP servers. Dehghani (2022) |

_Seeded 2026-07-22, HAND-MAINTAINED since — there is no generator. The original note credited a `gen_nested_claude.py` that exists in no commit and nowhere on disk; corrected 2026-07-31 so nobody hunts for it or assumes a regeneration will clear drift. Update this file in the same commit as the code. Guarded by `scripts/ci/doc_code_consistency.py`: E1/E2 that every path and module reference resolves, E5 that the declared module count matches the package._
