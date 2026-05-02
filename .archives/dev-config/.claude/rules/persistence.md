---
paths:
  - "src/cohezion/persistence/**"
  - "src/cohezion/core/persistence/**"
---

# Persistence & Database Rules

- SurrealDB connection: `ws://localhost:8001/rpc`, namespace `cohezion`, database `genesis`
- Use `cohezion.core.persistence.surreal_client` as the single entry point — do not create ad-hoc websocket connections
- All DB operations must use `get_circuit()` circuit breaker from `cohezion.reliability`
- Repository pattern: abstract repos in `repositories/` with Surreal-specific implementations prefixed `surreal_`
- Every DB call must have an explicit timeout
- Prefer batch operations over individual queries for token/latency efficiency
