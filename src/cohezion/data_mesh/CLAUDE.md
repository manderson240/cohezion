# data_mesh — Local Context

This file loads in addition to the root `CLAUDE.md`. Root applies here too.

**Purpose:** Data Mesh architecture for Cohezion's multi-agent system. Maps Zhamak Dehghani's 4 Data Mesh principles to Cohezion: 1. Domain ownership → Each specialist agent owns its data domain 2. Data as product

## Entry points (12 modules)

| Module | Key class(es) | LOC |
|---|---|---|
| `audio_telemetry.py` | `TaxonomyLevel`, `BirdSpeciesNode`, `AudioSegmentMetadata` | 80 |
| `corpus_quality_consumer.py` | `CorpusQualityConsumer` | 142 |
| `data_product.py` | `DataProductStatus`, `DataQualityTier`, `DataProductSchema` | 259 |
| `event_bridge.py` | `DataMeshEventBridge` | 289 |
| `event_consumer.py` | `EventConsumer` | 216 |
| `gaia_domain_agent.py` | `GaiaDataAgent` | 215 |
| `journey_telemetry.py` | `HardwareTier`, `SwarmExpert`, `QuadratureFabrics` | 93 |
| `lemonade_multimodal.py` | `LemonadeMultimodalClient` | 142 |
| `research_products.py` | `ResearchFinding` | 495 |
| `universe_telemetry.py` | `UniverseStateEvent` | 52 |

## Invariants / notes referencing this package (from harness.md / root CLAUDE.md)

- | `src/cohezion/data_mesh/data_product.py` | **DATA MESH** | Typed data products with SLA for 17+ MCP servers. Dehghani (2022) |

_Auto-generated 2026-07-22 (gen_nested_claude.py): facts deterministic (ast/grep), Purpose from __init__/module docstrings. Validated by scripts/ci/doc_code_consistency.py. Hand-enrich as needed._
