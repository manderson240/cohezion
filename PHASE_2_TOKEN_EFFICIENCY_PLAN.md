# Phase 2: Token-Efficient Compound Engineering

**Status**: Ready to start (Session 30+)
**Goal**: 85 tok/sec → 155 tok/sec (1.81× improvement)
**Branch**: `feature/repository-management-workflow`
**Duration**: 7-10 hours (4 priorities, parallelizable)

---

## Executive Summary

Phase 1 established production-ready compound engineering with:
- ✅ 7-step self-improving pipeline
- ✅ 3-tier semantic cache with VAE embeddings
- ✅ Vault-guided skill selection
- ✅ Multi-agent team coordination
- ✅ 342+ tests, 0 regressions

Phase 2 optimizes token efficiency through:
1. **FLUME VAE Integration** — Replace hash fallback with learned embeddings
2. **Vault Query Optimization** — Hierarchical search (O(n) → O(log n))
3. **Observability Dashboard** — Metrics aggregation + trend tracking
4. **Production Deployment** — Feature flags + A/B testing + rollback

**Expected Result**: 1.81× throughput improvement with production-grade observability.

---

## Priority 1: FLUME VAE Integration (2-3 hours)

### Objective
Replace SHA-256 hash fallback with FLUME VAE learned embeddings in `vae_encoder.py`.

### Current State
- `vae_encoder.py` exists with VAE loading code
- Falls back to hash-based projection if VAE unavailable
- 45 tests passing (but VAE discrimination is hash-limited)

### Work Required

#### 1.1 Verify VAE Checkpoint Quality
```python
# In tests/flume/test_vae_encoder.py
def test_vae_discrimination():
    """Verify VAE provides better discrimination than hash."""
    cache = SemanticCache()

    # Same topic should have >0.95 similarity
    related_a = cache._text_to_embedding("machine learning models")
    related_b = cache._text_to_embedding("deep neural networks")
    sim_related = np.dot(related_a, related_b)

    # Different topics should have <0.70 similarity
    unrelated = cache._text_to_embedding("how to bake cookies")
    sim_unrelated = np.dot(related_a, unrelated)

    assert sim_related > sim_unrelated + 0.2
```

#### 1.2 Fix VAE Encoder Initialization
- Ensure checkpoint loads `encoder` + `mu_head` correctly
- Verify 256D normalized output
- Test deterministic + reproducible embeddings
- Benchmark VAE vs hash latency (<50ms per encode)

#### 1.3 Update Cache Tests
- Update thresholds in `test_semantic_cache_vae_integration.py`
- Verify L2 matching now uses real semantic similarity
- Test cross-session pattern matching (L3 vault)

#### 1.4 Measure L3 Hit Rate Improvement
```python
# Baseline (hash-based)
baseline_l3_hit_rate = 0.05  # ~5% with hash

# Post-VAE
target_l3_hit_rate = 0.15  # 15% with VAE

# Run: scripts/example_multi_agent_team_execution.py
# Measure: average L3 hit rate across 100 team executions
```

### Success Criteria
- ✅ Identical text: >0.99 similarity (already working)
- ✅ Related topics: >0.85 similarity (VAE improves from ~0.70)
- ✅ Unrelated topics: <0.65 similarity (VAE improves from ~0.68)
- ✅ L3 hit rate: 5% → 15%+
- ✅ All 45 VAE tests passing
- ✅ No performance regression (<50ms encoding)

### Files to Modify
- `src/cohezion/flume/vae_encoder.py` — Checkpoint loading validation
- `tests/flume/test_vae_encoder.py` — Discrimination tests
- `tests/cache/test_semantic_cache_vae_integration.py` — Updated thresholds
- `tests/compound/test_team_executor.py` — L3 hit rate measurement

---

## Priority 2: Vault Query Optimization (2-3 hours)

### Objective
Replace linear O(n) full-text search with O(log n) hierarchical lookup.

### Current State
- `mcp_client.vault_search()` does full-text scan across all patterns
- ~50-200ms latency per skill selection query
- No indexing or tagging support

### Work Required

#### 2.1 Add Metadata Indexing to Vault
```python
# New schema in vault patterns:
# Each pattern tagged with:
# - operation_type: "generate" | "analyze" | "search" | "transform" | "persist"
# - domain: "ml" | "nlp" | "cv" | "qa" | "general"
# - skill_category: "core" | "integration" | "utility"
# - performance_tier: "high" | "medium" | "low"

pattern_metadata = {
    "operation_type": "analyze",
    "domain": "nlp",
    "skill_category": "core",
    "performance_tier": "high",
    "coherence_score": 0.92,
    "efficiency_score": 0.85,
}
```

#### 2.2 Implement Hierarchical Search
```python
class HierarchicalVaultSearch:
    """O(log n) search via tagged lookup."""

    def search_by_operation(self, op_type: str, limit=5):
        """Fast lookup by operation type."""
        # Instead of full scan, query vault patterns by tag
        # Pattern: "patterns/operations/{op_type}/*"

    def search_by_domain(self, domain: str, limit=5):
        """Fast lookup by domain."""
        # Pattern: "patterns/domains/{domain}/*"

    def search_by_composite(self, op_type, domain, limit=5):
        """Fast lookup by multiple criteria."""
        # Uses index intersection
```

#### 2.3 Update SkillSelector Integration
```python
# In src/cohezion/compound/skill_selector.py
async def select_skills(self, ...):
    """Use hierarchical search for skill selection."""

    # Instead of: vault_search(f"{task_description}")
    # Use:
    search_results = await self.vault_client.search_by_operation(
        operation_type=task.operation_type,
        domain=self._infer_domain(task.description),
        limit=10
    )
```

#### 2.4 Benchmark Search Performance
```python
# Compare old vs new:
# - Full-text search: 50-200ms (variable)
# - Hierarchical search: 5-20ms (consistent)
# - Expected speedup: 5-10×
```

### Success Criteria
- ✅ Search latency: 50-200ms → 5-20ms
- ✅ Accuracy: Same top-K results as full-text
- ✅ Scalability: Sub-linear growth with vault size
- ✅ Backward compatible: Old patterns still searchable
- ✅ 41+ SkillSelector tests passing

### Files to Modify
- `src/cohezion/core/mcp_client.py` — Add hierarchical search methods
- `src/cohezion/compound/skill_selector.py` — Use hierarchical search
- `tests/compound/test_skill_selector.py` — Benchmark search latency
- `docs/vault_query_optimization.md` — New documentation

---

## Priority 3: Observability Dashboard (3-4 hours)

### Objective
Unified metrics aggregation endpoint with real-time trends.

### Current State
- Individual metrics collectors (cache, compound, execution)
- No unified view or trend tracking
- No real-time monitoring dashboard

### Work Required

#### 3.1 Unified Metrics Collector
```python
# New: src/cohezion/observability/unified_metrics.py

class UnifiedMetricsCollector:
    """Aggregate metrics across all subsystems."""

    def __init__(self):
        self.cache_stats = {}
        self.execution_stats = {}
        self.team_stats = {}
        self.skill_stats = {}
        self.timestamps = []

    def record_cache_event(self, tier, hit_or_miss):
        """Record L1/L2/L3 cache event."""

    def record_execution(self, skill, coherence, efficiency, success):
        """Record compound execution metrics."""

    def record_team_result(self, compound_score, success_rate):
        """Record team execution outcome."""

    def get_aggregated_metrics(self) -> dict:
        """Return current state of all metrics."""
        return {
            "cache": self._aggregate_cache_metrics(),
            "execution": self._aggregate_execution_metrics(),
            "team": self._aggregate_team_metrics(),
            "skill_performance": self._aggregate_skill_metrics(),
            "timestamp": time.time()
        }
```

#### 3.2 API Endpoints
```python
# In src/cohezion/api/metrics.py

@router.get("/metrics/unified")
async def get_unified_metrics():
    """Get current unified metrics."""
    return collector.get_aggregated_metrics()

@router.get("/metrics/trends")
async def get_metrics_trends(window_minutes: int = 60):
    """Get metrics trends over time window."""
    return collector.get_trends(window_minutes)

@router.get("/metrics/skills")
async def get_skill_performance():
    """Get per-skill performance ranking."""
    return collector.get_skill_rankings()
```

#### 3.3 Trend Analysis
```python
class MetricsTrendAnalyzer:
    """Detect trends and anomalies in metrics."""

    def detect_cache_improvement(self) -> float:
        """Percentage improvement in L1+L2+L3 hit rate over time."""

    def detect_performance_regression(self) -> bool:
        """Alert if compound score dropping."""

    def detect_skill_convergence(self) -> dict:
        """Which skills are converging on best performance."""
```

#### 3.4 Dashboard Frontend (Optional)
```html
<!-- src/cohezion/api/static/dashboard.html -->
<div>
  <h1>Compound Engineering Dashboard</h1>

  <section>
    <h2>Cache Performance</h2>
    <div>L1 Hit Rate: 45%</div>
    <div>L2 Hit Rate: 32%</div>
    <div>L3 Hit Rate: 15% ↑ (was 5%)</div>
    <div>Overall: 92% ↑ (was 87%)</div>
  </section>

  <section>
    <h2>Execution Metrics</h2>
    <div>Avg Coherence: 0.88</div>
    <div>Avg Efficiency: 0.82</div>
    <div>Success Rate: 96%</div>
    <div>Avg Latency: 1.2s</div>
  </section>

  <section>
    <h2>Team Performance</h2>
    <div>Compound Score: 0.894 ↑</div>
    <div>Avg Team Size: 3 agents</div>
    <div>Parallel Tasks: 87%</div>
  </section>

  <section>
    <h2>Skill Rankings</h2>
    <table>
      <tr><th>Skill</th><th>Coherence</th><th>Efficiency</th><th>Uses</th></tr>
      <tr><td>analyze_reports</td><td>0.92</td><td>0.85</td><td>147</td></tr>
      ...
    </table>
  </section>
</div>
```

### Success Criteria
- ✅ `/metrics/unified` returns all key metrics
- ✅ `/metrics/trends` shows 60-minute window trends
- ✅ `/metrics/skills` ranks skills by performance
- ✅ Detects cache improvement from Phase 1
- ✅ Detects performance regressions early
- ✅ Real-time updates (sub-second)

### Files to Create/Modify
- `src/cohezion/observability/unified_metrics.py` — Metrics aggregation
- `src/cohezion/api/metrics.py` — API endpoints
- `src/cohezion/observability/trends.py` — Trend analysis
- `src/cohezion/api/static/dashboard.html` — Dashboard (optional)
- `tests/observability/test_unified_metrics.py` — 20+ tests

---

## Priority 4: Production Deployment (2-3 hours)

### Objective
Production-ready rollout with feature flags, A/B testing, and rollback procedures.

### Current State
- All Phase 2 features complete
- No production deployment mechanics
- No feature flags or A/B testing infrastructure

### Work Required

#### 4.1 Feature Flags
```python
# New: src/cohezion/config/feature_flags.py

class FeatureFlags:
    """Runtime feature control."""

    # Phase 2 features
    ENABLE_VAE_CACHE = os.getenv("ENABLE_VAE_CACHE", "false").lower() == "true"
    ENABLE_HIERARCHICAL_SEARCH = os.getenv("ENABLE_HIERARCHICAL_SEARCH", "false")
    ENABLE_UNIFIED_METRICS = os.getenv("ENABLE_UNIFIED_METRICS", "false")

    # Rollout percentages (0-100)
    VAE_ROLLOUT_PCT = int(os.getenv("VAE_ROLLOUT_PCT", "100"))
    SEARCH_ROLLOUT_PCT = int(os.getenv("SEARCH_ROLLOUT_PCT", "100"))

# Usage:
if FeatureFlags.ENABLE_VAE_CACHE:
    cache = SemanticCache(vae_encoder=get_vae())
else:
    cache = SemanticCache()  # Hash fallback
```

#### 4.2 A/B Testing Framework
```python
# New: src/cohezion/observability/ab_testing.py

class ABTestFramework:
    """Compare old vs new implementations."""

    def run_comparison(self, control_fn, treatment_fn, num_trials=100):
        """Run A/B test comparing two implementations."""
        results = {
            "control": [],
            "treatment": []
        }

        for _ in range(num_trials):
            control_result = control_fn()
            treatment_result = treatment_fn()
            results["control"].append(control_result)
            results["treatment"].append(treatment_result)

        return self._analyze_results(results)

    def _analyze_results(self, results) -> ABTestResult:
        """Statistical analysis of A/B test results."""
        return ABTestResult(
            control_mean=np.mean(results["control"]),
            treatment_mean=np.mean(results["treatment"]),
            improvement_pct=(
                (np.mean(results["treatment"]) - np.mean(results["control"])) /
                np.mean(results["control"]) * 100
            ),
            p_value=self._compute_p_value(results),
            significant=self._is_significant(results)
        )
```

#### 4.3 Rollback Procedures
```python
# New: src/cohezion/deployment/rollback.py

class RollbackManager:
    """Safe rollback to previous state."""

    def create_snapshot(self):
        """Capture current state (metrics, config, cache)."""
        return {
            "timestamp": time.time(),
            "metrics": collector.get_aggregated_metrics(),
            "config": config.to_dict(),
            "cache_state": cache.get_stats(),
            "git_commit": get_current_commit()
        }

    def rollback_to_snapshot(self, snapshot):
        """Restore to previous state."""
        # Disable new features via flags
        config.ENABLE_VAE_CACHE = False
        config.ENABLE_HIERARCHICAL_SEARCH = False
        # Clear new cache entries
        cache.clear_l2()
        cache.clear_l3()
        # Restore previous config
        config.restore(snapshot["config"])
```

#### 4.4 Monitoring & Alerts
```python
# New: src/cohezion/observability/alerts.py

class AlertManager:
    """Detect anomalies and send alerts."""

    def check_compound_score_regression(self):
        """Alert if compound score drops below threshold."""
        current = self.get_latest_compound_score()
        baseline = self.get_baseline_compound_score()

        if current < baseline * 0.95:  # 5% regression threshold
            self.alert_regression(current, baseline)

    def check_cache_anomaly(self):
        """Alert if cache hit rate changes significantly."""

    def check_latency_regression(self):
        """Alert if p99 latency increases."""
```

### Success Criteria
- ✅ Feature flags control all Phase 2 features
- ✅ A/B test framework shows treatment > control
- ✅ Rollback restores previous state in <1 minute
- ✅ Monitoring detects regressions within 5 minutes
- ✅ Production deployment guide documented
- ✅ Zero production incidents in first 24 hours

### Files to Create/Modify
- `src/cohezion/config/feature_flags.py` — Feature control
- `src/cohezion/observability/ab_testing.py` — A/B testing
- `src/cohezion/deployment/rollback.py` — Rollback procedures
- `src/cohezion/observability/alerts.py` — Monitoring
- `docs/production_deployment.md` — Deployment guide

---

## Implementation Order

### Phase 2 Timeline (Parallelizable)

**Day 1 Morning** (2-3 hours)
- Priority 1: FLUME VAE Integration
- Verify VAE discrimination >0.25× better than hash
- Update cache tests, measure L3 hit rate

**Day 1 Afternoon** (2-3 hours)
- Priority 2: Vault Query Optimization
- Implement hierarchical search
- Benchmark 5-10× speedup

**Day 2 Morning** (3-4 hours)
- Priority 3: Observability Dashboard
- Build unified metrics collector
- Add API endpoints + trend analysis

**Day 2 Afternoon** (2-3 hours)
- Priority 4: Production Deployment
- Feature flags, A/B testing, rollback procedures
- Deployment guide

**Total**: 9-13 hours (can run Priorities 1-2 in parallel = 5-6 hours wall-clock)

---

## Success Metrics

### Token Efficiency
- **Baseline**: 85 tok/sec (Session 27 baseline)
- **Priority 1 Target**: 85 → 98 tok/sec (+15% from better caching)
- **Priority 2 Target**: 98 → 125 tok/sec (+28% from faster skill selection)
- **Priority 3 Target**: 125 → 145 tok/sec (+16% from overhead reduction)
- **Priority 4 Target**: 145 → 155 tok/sec (+7% from optimized deployment)
- **Overall Goal**: 85 → 155 tok/sec (1.81×)

### Cache Hit Rate
- **L1**: 40% (stable)
- **L2**: 30% (VAE: 25% → 35%, +40%)
- **L3**: 5% → 15% (VAE: +200%)
- **Overall**: 75% → 92% (+23%)

### Latency
- **Skill Selection**: 50-200ms → 5-20ms (5-10× improvement)
- **Cache Lookup**: <1ms → <0.5ms
- **Team Execution**: <2s → <1.5s

### Reliability
- **Regressions**: 0
- **Production Incidents**: 0 (first 24h)
- **Rollback Time**: <1 minute
- **Alert Detection**: <5 minutes

---

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| VAE checkpoint unavailable | High | Test checkpoint in tests before deploy |
| Search accuracy regression | High | Verify top-K results match full-text |
| Performance regression | High | A/B test before rollout, feature flag |
| Alert fatigue | Medium | Tune thresholds, Slack #alerts channel |
| Import cycle during refactor | Medium | Test imports immediately after changes |

---

## Deliverables

### Code (4,000+ lines)
- `vae_encoder.py` (50 lines modifications)
- `mcp_client.py` (150 lines additions)
- `unified_metrics.py` (300 lines)
- `feature_flags.py` (80 lines)
- `ab_testing.py` (200 lines)
- `rollback.py` (150 lines)
- `alerts.py` (150 lines)
- Test files (1,000+ lines)

### Documentation (3,000+ lines)
- `PHASE_2_TOKEN_EFFICIENCY_PLAN.md` (this file)
- `vault_query_optimization.md` (400 lines)
- `production_deployment.md` (400 lines)
- `observability_dashboard.md` (300 lines)
- API documentation updates

### Metrics & Analysis
- Baseline performance report
- Phase 2 improvement report
- A/B test results
- Comparison vs. Phase 1

---

## Success Criteria (Final)

✅ Token efficiency: 85 → 155 tok/sec (1.81×)
✅ Cache hit rate: 75% → 92% (+23%)
✅ Skill selection latency: 50-200ms → 5-20ms (5-10×)
✅ Production deployment: Safe, monitored, reversible
✅ Test coverage: 60+ new tests, 0 regressions
✅ Documentation: Complete guides + examples

---

## Next Steps (Post-Phase 2)

**Phase 3: Production Scaling**
- Distributed caching (Redis multi-instance)
- Advanced RL training (adversarial perturbations)
- Vault archival (old patterns → cold storage)
- Real-time learning feedback loops

**Phase 4: Research Integration**
- VLIW cycle optimization (<300 cycles)
- Anthropic application submission
- Academic publication on compound engineering
- Open-source release (Apache 2.0)

---

**Status**: Ready to start
**Branch**: `feature/repository-management-workflow`
**Approved By**: (Awaiting user approval)
**Last Updated**: 2026-02-09
