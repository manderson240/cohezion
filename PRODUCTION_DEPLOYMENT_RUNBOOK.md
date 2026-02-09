# Production Deployment Runbook
## Phase 5B + Phase 6 to Production

**Version**: 1.0
**Date**: 2026-02-09
**Audience**: DevOps, SRE, On-Call Engineers

---

## Pre-Deployment Verification (Before Starting)

### 1. Verify Test Status
```bash
# Run all core tests
uv run pytest tests/swarm/ tests/compound/ tests/cache/ tests/security/ tests/chaos/ tests/edge_cases/ -q --tb=no

# Expected result:
# 1,370 passing | 9 pre-existing failures
# Pass rate: 99.4%
```

### 2. Verify Monitoring Setup
```bash
# Check monitoring dashboard endpoints
curl http://localhost:8000/health
curl http://localhost:8000/metrics

# Expected: 200 OK responses
```

### 3. Verify Feature Flags
```bash
# Check feature flag configuration
grep -r "COST_OPTIMIZATION_ENABLED" src/
grep -r "ANALYTICS_ENABLED" src/
grep -r "ANOMALY_DETECTION_ENABLED" src/

# Expected: All flags present and configurable
```

### 4. Brief Operations Team
- [ ] Explain Phase 5B changes (multi-agent coordination, cost optimization)
- [ ] Explain Phase 6 changes (cost routing, anomaly detection, chaos testing)
- [ ] Walk through alert thresholds
- [ ] Confirm rollback procedure understood
- [ ] Confirm monitoring dashboard accessible

---

## Deployment Steps

### Step 1: Code Review & Approval (30 min)

**Who**: Tech Lead or Architect

1. Review changes:
   ```bash
   git log --oneline main -20
   git diff HEAD~20...HEAD --stat
   ```

2. Verify key changes:
   - ✅ RedisSemanticCache integration
   - ✅ SkillConsensusVoter voting logic
   - ✅ CostAwareRouter cost optimization
   - ✅ GlobalMetricsAggregator dashboards
   - ✅ SessionPersistence vault storage
   - ✅ ModelRanker ranking logic
   - ✅ ModelFallbackStrategy circuit breaker
   - ✅ CostDashboard monitoring
   - ✅ ForecastEngine predictions
   - ✅ AnomalyDetector anomalies

3. Approve if all changes reviewed

### Step 2: Tag Release (5 min)

**Who**: DevOps Lead

```bash
# Tag the release
git tag -a phase-5b-6-v1.0 -m "Phase 5B QA-Approved + Phase 6 Complete (1,370 tests passing, 99.4%)"
git push origin phase-5b-6-v1.0

# Verify tag
git describe --tags
```

### Step 3: Pre-Deployment Health Check (15 min)

**Who**: DevOps Lead

1. Verify all services healthy:
   ```bash
   # Check main service
   curl -s http://localhost:8000/health | jq .

   # Check Redis (if deployed)
   redis-cli ping

   # Check Ollama models available
   curl -s http://localhost:11434/api/tags | jq .models[]
   ```

2. Verify configuration:
   ```bash
   # Check cost optimization config
   python -c "from cohezion.swarm.cost_aware_router import CostAwareRouter; print('CostAwareRouter OK')"

   # Check consensus voting config
   python -c "from cohezion.compound.skill_consensus_voter import SkillConsensusVoter; print('SkillConsensusVoter OK')"

   # Check metrics aggregator
   python -c "from cohezion.compound.global_metrics_aggregator import get_global_aggregator; print('GlobalMetricsAggregator OK')"
   ```

3. Verify monitoring:
   ```bash
   # Check Prometheus scrape targets
   curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets'

   # Check Grafana dashboards
   curl -s http://localhost:3000/api/dashboards/home
   ```

### Step 4: Canary Deployment (2 hour observation)

**Who**: DevOps Lead

#### 4a. Deploy to 10% Traffic
```bash
# Update load balancer routing (example for nginx):
# Route 10% to production-v2, 90% to production-v1
# sed -i 's/upstream backend.*/upstream backend { server prod-v1 weight=9; server prod-v2 weight=1; }/' /etc/nginx/nginx.conf
# nginx -s reload

# Alternative: Use feature flag
export COST_OPTIMIZATION_ENABLED=true
export ANALYTICS_ENABLED=true
export ANOMALY_DETECTION_ENABLED=true
export CHAOS_RECOVERY_ENABLED=true
```

#### 4b. Monitor (30 min observation)
```bash
# Watch error rate
watch -n 5 'curl -s http://localhost:8000/metrics | grep http_requests_total'

# Watch cost reduction
watch -n 5 'curl -s http://localhost:8000/metrics | grep cost_reduction_percent'

# Watch latency
watch -n 5 'curl -s http://localhost:8000/metrics | grep request_latency_seconds'

# Check alerts
curl -s http://localhost:9093/api/v1/alerts | jq '.data'
```

#### 4c: Health Checks During Canary
- [ ] Error rate stays < 0.01% (normal baseline)
- [ ] Cost reduction shows 25-35% savings
- [ ] Latency stable (±5% of baseline)
- [ ] No memory growth > 1GB
- [ ] Cache hit rate ≥ 95%
- [ ] Consensus rate ≥ 90%

#### 4d: Decision Point
- **✅ All metrics green**: Proceed to Phase 2 (25% traffic)
- **❌ Issues detected**: Rollback (see Emergency Rollback section)

### Step 5: Early Adoption Phase (25% traffic, 24 hours)

**Who**: DevOps Lead (+ 1 additional monitor)

1. Update routing:
   ```bash
   # sed -i 's/upstream backend.*/upstream backend { server prod-v1 weight=3; server prod-v2 weight=1; }/' /etc/nginx/nginx.conf
   # nginx -s reload
   ```

2. Monitor for 24 hours:
   - Cost reduction trend (should be consistent)
   - Error rate (should remain low)
   - Model distribution (should see cost-aware routing)
   - Consensus voting effectiveness

3. Review metrics:
   ```bash
   # Get 24h cost reduction trend
   curl -s 'http://localhost:9090/api/v1/query_range?query=cost_reduction_percent&start=<24h_ago>&end=now&step=1h' | jq .

   # Get consensus rate trend
   curl -s 'http://localhost:9090/api/v1/query_range?query=consensus_rate&start=<24h_ago>&end=now&step=1h' | jq .
   ```

4. Decision Point
   - **✅ All metrics green**: Proceed to Phase 3 (50% traffic)
   - **⚠️ Minor issues**: Tune parameters, extend observation
   - **❌ Issues detected**: Rollback

### Step 6: Broad Rollout Phase (50% traffic, 24 hours)

**Who**: DevOps Lead (+ 2 additional monitors)

1. Update routing:
   ```bash
   # sed -i 's/upstream backend.*/upstream backend { server prod-v1 weight=1; server prod-v2 weight=1; }/' /etc/nginx/nginx.conf
   # nginx -s reload
   ```

2. Monitor for 24 hours (same metrics as Phase 2)

3. Review cost impact over 24h:
   - Total cost savings accumulated
   - Per-model cost distribution
   - Anomaly detection effectiveness

4. Decision Point
   - **✅ All metrics green**: Proceed to Phase 4 (100% traffic)
   - **⚠️ Minor issues**: Tune parameters, extend observation
   - **❌ Issues detected**: Rollback

### Step 7: Full Production (100% traffic)

**Who**: DevOps Lead

1. Update routing:
   ```bash
   # sed -i 's/upstream backend.*/upstream backend { server prod-v2; }/' /etc/nginx/nginx.conf
   # nginx -s reload
   ```

2. Verify traffic:
   ```bash
   # All traffic should go to production-v2
   curl -s http://localhost:8000/metrics | grep http_requests_total
   ```

3. Continue monitoring (daily basis):
   - Daily cost reports
   - Weekly performance audits
   - Monthly architecture reviews

---

## Emergency Rollback Procedure

### Scenario 1: Error Rate Spike (> 0.1%)

**Immediate Actions** (< 2 minutes):

1. Trigger rollback:
   ```bash
   # Option A: Disable via feature flag
   export COST_OPTIMIZATION_ENABLED=false
   export ANALYTICS_ENABLED=false

   # Option B: Revert code
   git revert --no-edit <commit>
   git push
   ```

2. Verify rollback:
   ```bash
   curl -s http://localhost:8000/health
   curl -s http://localhost:8000/metrics | grep http_requests_total
   ```

3. Wait 5 minutes for error rate to normalize

4. Investigate:
   - Check logs: `docker logs <container> | tail -100`
   - Check metrics: Cost, latency, error rate trends
   - Check alerts: `curl http://localhost:9093/api/v1/alerts`

5. Post-mortem:
   - Document what went wrong
   - Fix underlying issue
   - Redeploy with corrected code

### Scenario 2: Cost Increase (> 10% vs baseline)

**Immediate Actions** (< 5 minutes):

1. Investigate root cause:
   ```bash
   # Check routing decisions
   curl -s http://localhost:8000/metrics | grep cost_aware_router_swaps

   # Check which models being used
   curl -s http://localhost:8000/metrics | grep model_routing_distribution
   ```

2. Options:
   - **Option A**: Disable cost optimization (feature flag)
     ```bash
     export COST_OPTIMIZATION_ENABLED=false
     ```
   - **Option B**: Adjust thresholds (temporary)
     ```bash
     export COST_THRESHOLD=0.20  # Increase threshold
     export LATENCY_THRESHOLD=50.0  # Decrease latency tolerance
     ```
   - **Option C**: Rollback entirely

3. Monitor after adjustment

### Scenario 3: Latency Increase (> 500ms)

**Immediate Actions** (< 5 minutes):

1. Check what's slow:
   ```bash
   curl -s http://localhost:8000/metrics | grep request_latency_seconds_bucket
   ```

2. Possibilities:
   - Consensus voting taking too long
   - Redis unavailable (fallback to local)
   - Model selection overhead too high

3. Quick fixes:
   - Disable consensus voting: `export CONSENSUS_STRATEGY=SINGLE_BEST`
   - Increase consensus timeout: `export CONSENSUS_TIMEOUT_MS=100`
   - Disable anomaly detection: `export ANOMALY_DETECTION_ENABLED=false`

4. If still slow: Rollback

### Scenario 4: Memory Leak (> 1GB growth)

**Immediate Actions** (< 10 minutes):

1. Check memory:
   ```bash
   curl -s http://localhost:8000/metrics | grep process_resident_memory_bytes
   docker stats --no-stream | grep <container>
   ```

2. Restart container (safest option):
   ```bash
   docker restart <container>
   ```

3. Investigate:
   - Check what's leaking
   - Look at vault persistence calls
   - Check session storage

4. Deploy fix after investigation

---

## Monitoring & Alerting

### Real-Time Dashboards

**Dashboard 1: Cost Optimization**
- URL: `http://localhost:3000/d/cost-optimization`
- Metrics:
  - Cost reduction percentage (red line = baseline, blue line = current)
  - Cost savings accumulated ($)
  - Model routing distribution (pie chart)
  - Cost per model

**Dashboard 2: Performance**
- URL: `http://localhost:3000/d/performance`
- Metrics:
  - Latency (p50, p95, p99)
  - Throughput (queries/sec)
  - Error rate (%)
  - Cache hit rate

**Dashboard 3: Consensus Voting**
- URL: `http://localhost:3000/d/consensus`
- Metrics:
  - Consensus rate (%)
  - Voting strategy distribution
  - Fallback frequency
  - Agreement percentage by team size

**Dashboard 4: Anomalies**
- URL: `http://localhost:3000/d/anomalies`
- Metrics:
  - Anomaly detection rate
  - False positive rate
  - Anomaly types (spike, trend, quality mismatch)
  - Detection latency

### Alert Configuration

**Critical Alerts** (Page On-Call):
1. Error rate spike: error_rate > 0.1% (↑ 10x)
2. Cost explosion: cost_per_query > 1.5x baseline
3. Latency increase: p95_latency > 500ms (↑ 2x)
4. Memory leak: rss_memory > 2GB

**Warning Alerts** (Slack Notification):
1. Cache hit drop: hit_rate < 90%
2. Consensus failure: consensus_rate < 85%
3. Model unavailable: fallback_frequency > 10%
4. Forecast accuracy: mape > 20%

### Daily Monitoring Checklist

**Morning (9 AM)**:
- [ ] Cost reduction on track (25-35%)
- [ ] Error rate normal (< 0.01%)
- [ ] Latency stable (±5% of baseline)
- [ ] No memory growth > 100MB/hour

**Evening (5 PM)**:
- [ ] Review daily cost savings
- [ ] Check weekly trend (should be consistent)
- [ ] Review anomalies detected
- [ ] Check consensus voting effectiveness

---

## Troubleshooting Guide

### Issue: Cost Reduction Not Appearing

**Symptoms**: Cost metrics show 0% reduction

**Investigation**:
1. Check if cost optimization is enabled:
   ```bash
   curl -s http://localhost:8000/metrics | grep cost_optimization_enabled
   ```

2. Check if routing decisions are being made:
   ```bash
   curl -s http://localhost:8000/metrics | grep cost_aware_router_swaps_total
   ```

3. Check if model costs are configured:
   ```bash
   grep -A 20 "model_cost_config" src/cohezion/swarm/cost_aware_router.py
   ```

**Solutions**:
- Verify feature flag is enabled
- Check model prices configuration
- Ensure alternative models available
- Review cost threshold settings

### Issue: Consensus Voting Failing

**Symptoms**: Consensus rate < 85%

**Investigation**:
1. Check voting strategy:
   ```bash
   curl -s http://localhost:8000/metrics | grep voting_strategy
   ```

2. Check agent agreement:
   ```bash
   curl -s http://localhost:8000/metrics | grep consensus_agreement_rate
   ```

3. Check voting latency:
   ```bash
   curl -s http://localhost:8000/metrics | grep voting_latency_seconds
   ```

**Solutions**:
- Switch to MAJORITY strategy (more lenient)
- Increase consensus timeout
- Reduce minimum agreement threshold
- Check agent coherence scores

### Issue: Anomaly Detector False Positives

**Symptoms**: Too many alerts for normal behavior

**Investigation**:
1. Check false positive rate:
   ```bash
   curl -s http://localhost:8000/metrics | grep anomaly_false_positive_rate
   ```

2. Check detection thresholds:
   ```bash
   grep -A 10 "spike_threshold\|trend_threshold" src/cohezion/compound/anomaly_detector.py
   ```

**Solutions**:
- Increase spike threshold (+20%)
- Increase trend threshold (+10%)
- Increase warm-up period (more history)
- Reduce detection sensitivity

---

## Post-Deployment Activities

### Day 1 (After Full Production)
- [ ] Monitor all dashboards continuously
- [ ] Review alerts (should be minimal)
- [ ] Check cost savings accumulating
- [ ] Verify no performance degradation

### Week 1
- [ ] Daily cost trend review
- [ ] Performance metrics stable
- [ ] Consensus voting working
- [ ] Anomaly detection effective

### Week 2-4 (Monthly Audit)
- [ ] Cost savings vs target
- [ ] Performance stability
- [ ] Team consensus effectiveness
- [ ] Plan next optimization phase

---

## Rollback Checklist

If needed to rollback to pre-Phase-5B/6:

- [ ] Disable feature flags (fast)
- [ ] Revert git commits (slower, ~5 min)
- [ ] Restart services (< 2 min)
- [ ] Verify traffic routing reverted
- [ ] Confirm metrics back to baseline
- [ ] Alert on-call if not automatic
- [ ] Schedule post-mortem

---

## Contact Information

**On-Call Engineer**:
- Slack: @oncall
- Phone: [configured in PagerDuty]

**Engineering Lead**:
- Slack: @architect
- Phone: [configured in PagerDuty]

**DevOps Lead**:
- Slack: @devops-lead

---

## References

- **Performance Targets**: PRODUCTION_DEPLOYMENT_READINESS_REPORT.md
- **Architecture**: docs/phase-6-architecture.md
- **Monitoring Setup**: docs/monitoring-setup.md
- **Rollback Procedure**: This document (section: Emergency Rollback)

---

**Last Updated**: 2026-02-09
**Approved By**: QA Lead, DevOps Lead, Architect
**Status**: ✅ READY FOR DEPLOYMENT

