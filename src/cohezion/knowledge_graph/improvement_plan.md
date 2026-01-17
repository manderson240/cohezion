# System Improvement Plan

## Current State Analysis

### Health Check Results
| Metric | Status |
|--------|--------|
| Python Files | 51 |
| Skills | 27 (13 custom + 14 legacy) |
| Tests | 35 passing |
| Core Modules | 6/6 importing |

### Module Health
- ✅ cohezion.swarm.types
- ✅ cohezion.swarm.agents.base
- ✅ cohezion.mcp.registry
- ✅ cohezion.security.validators
- ✅ cohezion.healing
- ✅ cohezion.learning

---

## Priority Improvements

### P0: Critical (Production Blockers)

1. **Fix datetime deprecation warnings**
   - Files: `security/auth.py`, `security/audit.py`
   - Change: `datetime.utcnow()` → `datetime.now(datetime.UTC)`
   - Impact: Python 3.12+ compatibility

2. **Add missing __init__.py files**
   - Check all subdirectories for proper package structure

### P1: High (Performance/Reliability)

3. **Add connection pooling**
   - SurrealDB client should reuse connections
   - Ollama HTTP client needs connection limits

4. **Implement circuit breaker**
   - Self-healing should break on repeated failures
   - Prevent cascade failures

5. **Add Redis caching layer**
   - Rate limiter persistence
   - Response caching for repeated queries

### P2: Medium (Usability)

6. **FastAPI middleware integration**
   - Wire security/rate_limiter into API
   - Add request logging middleware

7. **Improve test coverage**
   - Add integration tests
   - Add API endpoint tests
   - Target: 80% coverage

8. **Documentation generation**
   - Auto-generate API docs
   - Skill index page

### P3: Low (Nice to Have)

9. **Prometheus metrics**
   - Add /metrics endpoint
   - Track: latency, errors, model usage

10. **WebSocket support**
    - Real-time debate streaming
    - Live visualization updates

---

## Novel Physics Explorations

### Simulation 1: Semantic Mass Dynamics
- **Hypothesis**: High-mass (importance) nodes attract related concepts
- **Metric**: Graph clustering coefficient vs. mass distribution

### Simulation 2: Coherence-Stability Relationship
- **Hypothesis**: Coherence correlates with temporal stability
- **Metric**: d(coherence)/dt predicts knowledge decay

### Simulation 3: Novelty-Connectivity Balance
- **Hypothesis**: High novelty predicts low initial connectivity
- **Metric**: Novelty × connectivity = constant for stable knowledge

### Simulation 4: Sentiment Wave Propagation
- **Hypothesis**: Sentiment changes propagate through connected nodes
- **Metric**: Sentiment diffusion rate in knowledge graph

### Simulation 5: Dimensional Entanglement
- **Hypothesis**: Some dimensions are fundamentally linked
- **Metric**: Correlation matrix of 12D states across time

---

## Implementation Priority

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | P0 fixes | Production-ready |
| 2 | P1 reliability | Pooling, circuit breaker |
| 3 | P2 usability | Middleware, tests |
| 4 | P3 observability | Metrics, WebSocket |
| 5 | Novel physics | Simulation results |
