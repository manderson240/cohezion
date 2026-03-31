"""Data Mesh architecture for Cohezion's multi-agent system.

Maps Zhamak Dehghani's 4 Data Mesh principles to Cohezion:
  1. Domain ownership → Each specialist agent owns its data domain
  2. Data as product  → Typed products with schema, SLA, ownership
  3. Self-serve platform → SurrealDB + Vault + SemanticCache
  4. Federated governance → Compound loop quality gates

Smith fabric mapping: Field fabric (data topology)
  Gauge invariance = governance consistency across domains

Attribution: Zhamak Dehghani, "Data Mesh: Delivering Data-Driven Value at Scale"
  (O'Reilly, 2022)
"""
