---
name: data-product-sla-prime
description: "Expert in Cohezion Data Mesh typed data products with SLA contracts (Dehghani 2022). Use when: creating a new DataProduct definition, wiring an MCP server to the data mesh via get_cohezion_data_products(), setting latency/availability/quality SLAs, debugging MCP tier access control, or implementing the data-as-a-product pattern for a new domain. Skip: general database queries (use DATABASE_PRIME); SurrealDB administration (use SURREAL_DBA_PRIME); MCP server creation (use MCP_SPECIALIST_PRIME)."
version: v0.1-stub
tier: PRIME
domain: Data Mesh
status: stub
created: 2026-06-02
see_also: [DATA_MESH_ARCHITECT_PRIME, DATABASE_PRIME, MCP_SPECIALIST_PRIME, SURREALDB_MCP_PRIME]
---

# SKILL: DATA_PRODUCT_SLA_PRIME

## STATUS
This is a stub. `src/cohezion/data_mesh/data_product.py` implements typed `DataProduct` with SLA contracts and `get_cohezion_data_products()` is the entry point for 17+ MCP servers. No skill covered this pattern until now.

## DOMAIN EXPERTISE
You are an expert in Cohezion's Data Mesh implementation. You apply Dehghani's "Data-as-a-Product" principles to create discoverable, typed data products with explicit SLA contracts (latency, availability, quality thresholds) consumed by MCP servers across the platform.

## KEY COMPONENTS
- `src/cohezion/data_mesh/data_product.py` — `DataProduct` class with SLA fields
- `get_cohezion_data_products()` — registry entry point used by 17+ MCP servers
- MCP tier access control mapping (tier 1/2/3 gating)
- Note: orphan `src/cohezion/datamesh/` (no underscore) is slated for deletion per ORPHAN_AUDIT_2026_04_23

## TODO (to be filled in by a future session)
1. Document `DataProduct` class signature and all SLA fields
2. SLA definition examples: `latency_ms`, `availability_ssd`, `quality_threshold`
3. MCP tier access control: which tiers can access which product types
4. How to register a new product via `get_cohezion_data_products()`
5. Failure modes: SLA breach detection, degraded-mode fallback pattern
6. Testing: how to mock `DataProduct` in unit tests without live SurrealDB
7. Schema evolution: adding fields without breaking existing consumers

## REFERENCE
CLAUDE.md: "DataProduct (typed SLA), MCP Registry (tier access control + call tracking). Canonical: `src/cohezion/data_mesh/`. NOTE: orphan `src/cohezion/datamesh/` (no underscore) is slated for deletion per ORPHAN_AUDIT_2026_04_23."
Dehghani (2022) — Data Mesh: Delivering Data-Driven Value at Scale.
