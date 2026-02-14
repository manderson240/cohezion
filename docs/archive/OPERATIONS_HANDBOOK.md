# Operations Handbook
## Phase 5B + Phase 6 Production Operations

**Version**: 1.0
**Effective Date**: 2026-02-09
**Audience**: DevOps, SRE, On-Call Engineers
**Maintenance**: Update quarterly or after major incidents

---

## Quick Reference

### Key Metrics to Monitor

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Cost Deviation | ±10% | ±15% | >±20% |
| Query Latency P99 | <100ms | <200ms | >200ms |
| Cache Hit Rate | >90% | >80% | <80% |
| Error Rate | <0.1% | <0.5% | >0.5% |
| GPU Utilization | <70% | <85% | >85% |
| Budget Used | <75% | <90% | >90% |
| Team Consensus Rate | >90% | >85% | <85% |

### Critical URLs

```
Production Dashboard:     https://cohezion.io/dashboard/
Cost Monitor:            https://cohezion.io/costs/
Metrics/Prometheus:      https://cohezion.io/metrics
Alerts/Grafana:          https://cohezion.io/alerts
Team Status:             https://cohezion.io/team/
Health Check:            https://cohezion.io/health
```

### Key Contact Info

```
On-Call Engineer:  ${ON_CALL_EMAIL}
DevOps Slack:      #cohezion-devops
Escalation:        @devops-lead, @architecture
```

---

## Section 1: Daily Operations

### 1.1 Morning Checklist (Start of Shift)

**Time**: 9:00 AM
**Duration**: 15 minutes

```bash
# 1. Verify system health
curl https://cohezion.io/health
# Expected: 200 OK, all services green

# 2. Check overnight alerts
curl https://cohezion.io/alerts/last-24h
# Expected: No critical alerts, <5 warnings

# 3. Review cost dashboard
# Check: Cost trend, anomalies, budget status
# Expected: Costs within ±20% of baseline

# 4. Verify deployment status
kubectl get pods -n cohezion
# Expected: All pods running, 0 restarts in last hour

# 5. Check error logs
kubectl logs -n cohezion --tail=100 | grep ERROR
# Expected: <5 error lines per service

# 6. Confirm database connectivity
psql -h db.prod -d cohezion -c "SELECT COUNT(*) FROM metrics;"
# Expected: Query returns row count
```

### 1.2 Hourly Health Check (During Business Hours)

**Time**: Every hour, 9-5 PM
**Duration**: 5 minutes

```bash
# 1. Quick metrics check
curl https://cohezion.io/metrics | grep "queries_per_second"
# Expected: 1000-5000 queries/sec

# 2. Alert status
curl https://cohezion.io/alerts/active
# Expected: 0 critical alerts

# 3. Cache stats
curl https://cohezion.io/metrics | grep "cache_hit"
# Expected: >90% hit rate

# 4. Latency check
curl https://cohezion.io/metrics | grep "query_latency_ms_p99"
# Expected: <100ms
```

### 1.3 End of Shift Checklist (5:00 PM)

**Time**: Before shift ends
**Duration**: 10 minutes

```bash
# 1. Archive daily metrics
./scripts/ops/archive_daily_metrics.sh $(date +%Y-%m-%d)

# 2. Generate daily report
./scripts/ops/generate_daily_report.sh > reports/$(date +%Y-%m-%d).md

# 3. Brief on-call engineer for night shift
# Include: cost status, any warnings, upcoming maintenance

# 4. Verify backups completed
ls -lh /backups/$(date +%Y-%m-%d)/ | wc -l
# Expected: >10 backup files

# 5. Check tomorrow's planned maintenance
cat /ops/maintenance_calendar.txt
# Expected: No emergency maintenance scheduled
```

---

## Section 2: Monitoring & Alerting

### 2.1 Key Dashboards

#### Cost Dashboard
**URL**: https://cohezion.io/dashboard/costs
**Refresh**: Every 30 seconds
**Key Panels**:
- Cost trend (last 24h)
- Cost by model (pie chart)
- Budget vs actual
- Cost anomalies
- Alert level (green/yellow/red)

**What to Look For**:
- ✅ Green alert level (normal)
- ✅ Cost within baseline ±20%
- ✅ Budget utilization <80%
- ✅ No new anomalies

**Action if Alert**:
1. Click "View Details" for affected models
2. Check if queries increased (expected) or costs increased (investigate)
3. If cost spike: notify engineering team
4. If budget warning: implement query throttling

#### Metrics Dashboard
**URL**: https://cohezion.io/metrics
**Format**: Prometheus metrics
**Key Metrics**:
- `queries_per_second` - QPS
- `query_latency_ms_p50` - Median latency
- `query_latency_ms_p99` - 99th percentile latency
- `cache_hit_rate` - Semantic cache effectiveness
- `model_quality_score` - Degradation tracking
- `consensus_rate` - Team voting consensus

**Alert Thresholds**:
- QPS spike >2x baseline: investigate
- P99 latency >200ms: check GPU/CPU
- Cache hit <80%: review cache config
- Quality score <80%: check model performance

#### Alerts Dashboard
**URL**: https://cohezion.io/alerts
**Format**: Grafana alerts
**Active Alerts Show**:
- Alert name and severity
- Duration active
- Affected component
- Recommended action

**Alert Types**:
1. **Cost Spike** (>20% deviation)
   - Action: Review anomaly detector, check if expected

2. **Budget Warning** (>80% used)
   - Action: Implement query throttling, notify stakeholders

3. **Quality Degradation** (>20% drop)
   - Action: Review model metrics, check for failures

4. **Latency High** (P99 >200ms)
   - Action: Check hardware utilization, review query patterns

5. **Consensus Failure** (<85% rate)
   - Action: Review team voting logs, check for agent failures

### 2.2 Alert Response Procedures

#### Cost Spike Alert

**Severity**: 🟡 Warning or 🔴 Critical (depends on magnitude)

**Response**:
```
1. Check anomaly detector dashboard
   - View spike detection results
   - Review confidence score
   - Identify affected models/queries

2. Determine if expected
   - Were there recent deployments? → Expected
   - Was query volume high? → Expected
   - Did model change? → Expected
   - Otherwise → Unexpected

3. If unexpected
   a. Review cost trends (last 24h)
   b. Check for new patterns
   c. Investigate affected models
   d. Escalate to engineering if persistent

4. If critical (>50% increase)
   a. Implement emergency query throttling
   b. Notify stakeholders immediately
   c. File incident report
   d. Plan remediation
```

#### Budget Alert

**Severity**: 🟡 Warning (80-90%) or 🔴 Critical (>90%)

**Response**:
```
1. Check current budget status
   - View budget used vs limit
   - Calculate remaining runway
   - Estimate usage for rest of period

2. If warning (80-90%)
   a. Implement query rate limiting
   b. Prioritize high-value queries
   c. Monitor for next 2 hours
   d. Notify stakeholders of status

3. If critical (>90%)
   a. Activate emergency throttling
   b. Fail non-critical queries
   c. Prioritize production traffic
   d. Notify all stakeholders
   e. File emergency incident

4. Recovery
   - Wait for budget reset (usually daily)
   - Post-incident review after budget restored
   - Plan capacity for next period
```

#### Latency Alert

**Severity**: 🟡 Warning (>150ms) or 🔴 Critical (>300ms)

**Response**:
```
1. Diagnose cause
   - Check GPU utilization: kubectl top nodes
   - Check CPU utilization: kubectl top pods
   - Check memory: kubectl describe nodes
   - Check query queue depth

2. Quick fixes
   a. If GPU >90%: reduce batch size
   b. If CPU >90%: scale up pods (kubectl scale)
   c. If memory >90%: restart affected pods
   d. If queue deep: check for stuck queries

3. If issue persists
   a. Reduce concurrent queries
   b. Enable caching more aggressively
   c. Route to fallback models if available
   d. Notify engineering team

4. Post-incident
   - Scale back to normal once resolved
   - Document issue for weekly review
```

#### Quality Degradation Alert

**Severity**: 🟡 Warning (15-20% drop) or 🔴 Critical (>20% drop)

**Response**:
```
1. Check degradation details
   - Which models affected?
   - How severe is drop?
   - Is trend or spike?

2. Possible causes
   - New model version deployed (expected)
   - Hardware issues (check GPU health)
   - Data quality issues (check query patterns)
   - Model overfitting (check training data)

3. Quick fixes
   a. If recent deployment: check release notes
   b. If hardware issue: restart pods, check GPU
   c. If data issue: review recent queries
   d. If overfitting: reduce model complexity

4. Escalation
   - If critical: notify ML engineering
   - If persistent: file technical debt issue
```

---

## Section 3: Common Issues & Troubleshooting

### 3.1 High Cost

**Symptom**: Cost spike detected, budget warning triggered

**Diagnosis**:
```bash
# 1. Check cost by model
curl https://cohezion.io/metrics | grep "cost_by_model"

# 2. Check query volume
curl https://cohezion.io/metrics | grep "queries_per_second"

# 3. Check model changes
git log --oneline --since="1 hour" | grep -i "model\|router"

# 4. Check routing decisions
tail -100 /var/log/cohezion/routing.log | grep "SWAP\|MODEL_SELECT"
```

**Fixes** (try in order):
1. **Increase threshold**
   ```python
   # File: config.yaml
   cost_aware_router:
     cost_threshold: 0.20  # Increase from 0.10 (10%) to 0.20 (20%)
   ```

2. **Prefer cheaper models**
   ```python
   # File: config.yaml
   cost_aware_router:
     prefer_longer_models_if_cheaper_per_token: true
     latency_threshold: 200  # Increase from 100ms to 200ms
   ```

3. **Implement query throttling**
   ```bash
   kubectl set env deployment/cohezion QUERY_RATE_LIMIT=100  # queries/sec
   ```

4. **Scale to cheaper models**
   ```bash
   kubectl scale deployment/cohezion-phi3 --replicas=5  # increase cheap model
   kubectl scale deployment/cohezion-gpt4 --replicas=2  # reduce expensive model
   ```

### 3.2 High Latency

**Symptom**: Query latency P99 >200ms, operations slow

**Diagnosis**:
```bash
# 1. Check hardware utilization
kubectl top nodes
kubectl top pods -n cohezion

# 2. Check query patterns
curl https://cohezion.io/metrics | grep "queries_per_second"

# 3. Check cache hit rates
curl https://cohezion.io/metrics | grep "cache_hit_rate"

# 4. Check model response times
tail -100 /var/log/cohezion/models.log | grep "latency"
```

**Fixes** (try in order):
1. **Enable aggressive caching**
   ```python
   # File: config.yaml
   semantic_cache:
     similarity_threshold: 0.90  # More lenient matching
     max_entries: 2000  # Increase cache size
   ```

2. **Scale up resources**
   ```bash
   kubectl scale deployment/cohezion --replicas=10  # increase pods
   kubectl set resources deployment/cohezion --limits=memory=16Gi,cpu=4  # more per-pod
   ```

3. **Reduce batch size**
   ```python
   # File: config.yaml
   batch:
     parallel_tasks: 4  # Reduce from 8
     max_batch_size: 20  # Reduce from 50
   ```

4. **Route to faster models**
   ```bash
   kubectl set env deployment/cohezion PREFER_LOCAL_MODELS=true  # use phi3:mini
   ```

### 3.3 Low Cache Hit Rate

**Symptom**: Cache hit rate <80%, queries slower than expected

**Diagnosis**:
```bash
# 1. Check cache size
curl https://cohezion.io/metrics | grep "cache_entries"

# 2. Check cache evictions
curl https://cohezion.io/metrics | grep "cache_evictions"

# 3. Check query patterns
tail -100 /var/log/cohezion/cache.log | grep "MISS"
```

**Fixes**:
1. **Warm cache**
   ```bash
   python scripts/cache_warmer.py --patterns 1000
   ```

2. **Increase cache size**
   ```python
   # File: config.yaml
   semantic_cache:
     max_entries: 2000  # Increase from 1000
   ```

3. **Lower similarity threshold**
   ```python
   # File: config.yaml
   semantic_cache:
     similarity_threshold: 0.85  # Lower from 0.95 for more fuzzy matches
   ```

4. **Debug specific query patterns**
   ```bash
   tail -100 /var/log/cohezion/cache.log | grep "MISS" | head -5
   # Review log entries to understand patterns
   ```

### 3.4 Budget Exceeded

**Symptom**: Budget used >100%, queries failing

**Emergency Response**:
```bash
# 1. Enable emergency throttling
kubectl set env deployment/cohezion EMERGENCY_THROTTLE=true QUERY_RATE_LIMIT=10

# 2. Fail non-critical requests
# Edit routing to prioritize production
kubectl set env deployment/cohezion PROD_ONLY_MODE=true

# 3. Increase cost thresholds
kubectl set env deployment/cohezion COST_THRESHOLD=0.50  # Aggressive cost cutting

# 4. Switch to cheapest models
kubectl set env deployment/cohezion FORCE_CHEAP_MODELS=true
```

**Recovery**:
```bash
# Wait for budget reset (usually next day)
# Check when budget resets
curl https://cohezion.io/budget/reset-time

# Once reset, gradually return to normal
kubectl set env deployment/cohezion PROD_ONLY_MODE=false
kubectl set env deployment/cohezion EMERGENCY_THROTTLE=false
kubectl set env deployment/cohezion QUERY_RATE_LIMIT=1000  # restore
```

### 3.5 Team Consensus Failure

**Symptom**: Consensus rate <85%, voting failures

**Diagnosis**:
```bash
# 1. Check agent status
curl https://cohezion.io/team/agents
# Expected: All agents green

# 2. Check voting results
tail -100 /var/log/cohezion/voting.log | grep "FAILURE"

# 3. Check network connectivity
ping -c 5 agent-1.cohezion.svc.cluster.local
ping -c 5 agent-2.cohezion.svc.cluster.local
```

**Fixes**:
1. **Restart failed agents**
   ```bash
   kubectl rollout restart deployment/cohezion-agents
   ```

2. **Check networking**
   ```bash
   kubectl get networkpolicy -n cohezion
   # Verify agents can reach each other
   ```

3. **Review voting logs**
   ```bash
   tail -1000 /var/log/cohezion/voting.log | grep "ERROR" | wc -l
   ```

---

## Section 4: Maintenance & Updates

### 4.1 Scheduled Maintenance

**Weekly Maintenance Window** (Sunday 2-4 AM UTC)
- No production queries routed
- Database maintenance runs
- Log rotation
- Cache cleanup

**Procedure**:
```bash
# 1. Notify operations team
# 2. Redirect traffic to standby cluster
# 3. Run maintenance tasks
# 4. Verify all systems healthy
# 5. Switch traffic back
# 6. Confirm operations team
```

### 4.2 Updates & Patches

**Security Patches**:
- Apply immediately to staging
- Test for 1 hour
- Deploy to production during maintenance window

**Feature Updates**:
- Plan 1-2 weeks in advance
- Use feature flags for gradual rollout
- Monitor carefully for first 24 hours

**Breaking Changes**:
- Coordinate with all stakeholders
- Plan migration period (2-4 weeks)
- Provide tools and scripts for migration

---

## Section 5: Incident Management

### 5.1 Incident Severity

| Severity | Impact | Response Time | Example |
|----------|--------|----------------|---------|
| P1 | Total outage | Immediate | All queries failing |
| P2 | Severe degradation | 15 minutes | Cost 2x normal, latency >1s |
| P3 | Moderate issue | 1 hour | Cost 50% above normal |
| P4 | Minor issue | Next business day | Documentation typo |

### 5.2 Incident Response

**For Any Incident**:
1. **Assess severity** (P1-P4)
2. **Activate incident commander** (for P1-P2)
3. **Implement immediate fix** (if safe)
4. **Document issue** (timeline, root cause, fix)
5. **Post-incident review** (within 24 hours)

**For P1 Incidents** (Total Outage):
```
0 min:   Declare incident, page on-call team
5 min:   Initial diagnosis, activate war room
10 min:  Root cause hypothesis
15 min:  Implement immediate fix
20 min:  Verify fix works, restore operations
30 min:  Stakeholder communication
60 min:  Post-incident review scheduled
```

---

## Section 6: Escalation & Contacts

### 6.1 Escalation Path

```
Level 1: On-Call Engineer
- Can resolve: Restart pods, scale resources, implement feature flags
- Response time: 15 minutes

Level 2: DevOps Lead
- Can resolve: Code changes, deployment decisions, architecture questions
- Response time: 30 minutes

Level 3: Architecture/Engineering Leadership
- Can resolve: Major decisions, emergency rollbacks, stakeholder communication
- Response time: 1 hour
```

### 6.2 Contact Information

```
On-Call Schedule: ops/oncall.txt
DevOps Slack: #cohezion-devops
Engineering Slack: #cohezion-eng
PagerDuty: https://pagerduty.com/oncall/cohezion
```

---

## Appendix: Quick Commands

```bash
# Check system health
kubectl get pods -n cohezion
kubectl describe nodes

# View logs
kubectl logs -n cohezion deployment/cohezion --tail=100
kubectl logs -n cohezion deployment/cohezion --timestamps=true --since=1h

# Scale deployment
kubectl scale deployment/cohezion --replicas=5

# Restart pods
kubectl rollout restart deployment/cohezion

# Check metrics
curl https://cohezion.io/metrics | head -50

# Check alerts
curl https://cohezion.io/alerts/active

# View cost dashboard
open https://cohezion.io/dashboard/costs

# Emergency throttling
kubectl set env deployment/cohezion QUERY_RATE_LIMIT=10

# Restore normal operations
kubectl set env deployment/cohezion QUERY_RATE_LIMIT=1000
```

---

**Document Version**: 1.0
**Last Updated**: 2026-02-09
**Next Review**: 2026-05-09 (quarterly)

