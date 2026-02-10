# Comprehensive Deployment Runbook - Cohezion Framework

**Date**: February 9, 2026
**Version**: 1.0
**Audience**: DevOps Team, Operations Engineers
**Purpose**: Step-by-step procedures for production deployment

---

## Table of Contents

1. [Pre-Deployment Phase](#pre-deployment-phase)
2. [Canary Deployment Phase](#canary-deployment-phase)
3. [Full Production Rollout](#full-production-rollout)
4. [Post-Deployment Monitoring](#post-deployment-monitoring)
5. [Troubleshooting Guide](#troubleshooting-guide)
6. [Rollback Procedures](#rollback-procedures)
7. [Success Criteria](#success-criteria)
8. [Configuration Reference](#configuration-reference)

---

## PRE-DEPLOYMENT PHASE

**Duration**: ~30 minutes
**Owner**: DevOps Team
**Gates**: Must pass all checks before proceeding

### Phase 1.1: Infrastructure Readiness

**Objective**: Verify infrastructure is prepared for deployment

#### 1.1.1 Python Runtime Verification
```bash
# Verify Python 3.13+ is available
python3 --version  # Expected: Python 3.13.x or higher

# Verify pip/uv available
uv --version       # Expected: uv 0.x.x or higher

# Verify venv support
python3 -m venv --help  # Should work without error
```

**Success Criteria**:
- [x] Python 3.13+ confirmed
- [x] uv package manager available
- [x] venv support functional

#### 1.1.2 Database Readiness
```bash
# Verify SurrealDB connection
# Expected endpoint: ws://localhost:8000/rpc

# Test basic connectivity
curl -i http://localhost:8000/

# Or test via Python
python3 << 'EOF'
import asyncio
from surrealdb import Surreal

async def test_surreal():
    async with Surreal('ws://localhost:8000/rpc') as db:
        await db.use('cohezion', 'core')
        result = await db.query('SELECT * FROM $auth')
        print("SurrealDB connection OK")

asyncio.run(test_surreal())
EOF
```

**Success Criteria**:
- [x] SurrealDB accessible at ws://localhost:8000/rpc
- [x] Authentication configured
- [x] Namespace 'cohezion' available
- [x] Database 'core' created

#### 1.1.3 Model Service Readiness
```bash
# Verify Ollama service running
curl http://localhost:11434/api/tags

# Expected models for Cohezion
# - deepseek-r1:70b
# - qwen3-coder:30b
# - phi3:mini

# Test model availability
ollama list

# If models not available, pull them:
ollama pull deepseek-r1:70b
ollama pull qwen3-coder:30b
ollama pull phi3:mini
```

**Success Criteria**:
- [x] Ollama service accessible at localhost:11434
- [x] Models available: deepseek-r1:70b, qwen3-coder:30b, phi3:mini
- [x] Model concurrency limit set to 4 (verify in Ollama config)

#### 1.1.4 Optional: Redis Configuration
```bash
# If using RedisSemanticCache (L3 distributed cache)
redis-cli ping
# Expected: PONG

# Verify Redis accessibility
redis-cli CONFIG GET port
# Expected: 6379 (or your configured port)
```

**Success Criteria** (if using Redis):
- [x] Redis service accessible
- [x] Redis configured and started
- [x] No AUTH required or credentials configured in code

### Phase 1.2: Code Verification

**Objective**: Verify code baseline and tests passing

#### 1.2.1 Repository State
```bash
cd /path/to/cohezion

# Verify clean state or expected commits
git status
git log --oneline -5

# Expected: Session 46 or later baseline
# Expected status: clean or only expected changes
```

**Success Criteria**:
- [x] Latest code pulled from repository
- [x] No unexpected uncommitted changes
- [x] On main branch or expected feature branch

#### 1.2.2 Test Suite Verification
```bash
# Install dependencies
uv sync

# Run full test suite
uv run pytest tests/compound/ tests/cache/ tests/security/ tests/test_*.py -q

# Expected: ~634+ tests, 98.5%+ pass rate
```

**Success Criteria**:
- [x] Pytest runs successfully
- [x] No import errors
- [x] Test pass rate ≥98.5%
- [x] Zero test failures (or only expected skips)

#### 1.2.3 Security Configuration
```bash
# Verify security framework installed
python3 << 'EOF'
from cohezion.security.guardrail_pipeline import GuardrailPipeline
print("GuardrailPipeline: OK")

from cohezion.security.auth.api_key_auth import APIKeyAuth
print("APIKeyAuth: OK")
EOF

# Verify pre-commit hooks configured
cat .pre-commit-config.yaml | grep -E "(bandit|detect-secrets)"
# Expected: Both tools present
```

**Success Criteria**:
- [x] Security modules import correctly
- [x] Pre-commit hooks configured
- [x] Guardrail pipeline available

### Phase 1.3: Build & Artifact Creation

**Objective**: Create deployment artifact

#### 1.3.1 Clean Build
```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info

# Create source distribution
uv build

# Expected output: dist/cohezion-x.x.x.tar.gz
# Expected: Successful build with no errors
```

**Success Criteria**:
- [x] Build completes without errors
- [x] Artifact created in dist/
- [x] Artifact size reasonable (not > 500MB)

#### 1.3.2 Artifact Verification
```bash
# List artifact
ls -lh dist/

# Verify tar contents (sample)
tar -tzf dist/cohezion-*.tar.gz | head -20

# Expected: src/cohezion/ present, setup.py/pyproject.toml present
```

**Success Criteria**:
- [x] Artifact created and readable
- [x] Contains all source code
- [x] Contains pyproject.toml and configuration

### Phase 1.4: Team Preparation

**Objective**: Prepare operational team for deployment

#### 1.4.1 Team Briefing
- [ ] Brief DevOps team on deployment plan
- [ ] Distribute runbook to all team members
- [ ] Confirm on-call team assignments
- [ ] Establish communication channel (Slack/Discord)
- [ ] Set up war room (optional but recommended)

#### 1.4.2 Access & Credentials
- [ ] Verify all team members have access to infrastructure
- [ ] Verify API keys/secrets are available
- [ ] Verify database credentials configured
- [ ] Document any access requirements

#### 1.4.3 Monitoring Setup
- [ ] Confirm monitoring dashboards available
- [ ] Verify alert notification channels working
- [ ] Test alert escalation paths
- [ ] Confirm on-call team receives alerts

### Phase 1.5: Final Go/No-Go Decision

**Decision Gate**: Can we proceed to canary deployment?

#### 1.5.1 Pre-Deployment Checklist
```
PRE-DEPLOYMENT CHECKLIST
═════════════════════════════════════════════════════════

INFRASTRUCTURE
[ ] Python 3.13+ available
[ ] SurrealDB accessible (ws://localhost:8000/rpc)
[ ] Ollama running with required models
[ ] Redis available (if using RedisSemanticCache)
[ ] Network connectivity verified

CODE & TESTING
[ ] Repository at expected state
[ ] Tests passing (≥98.5%)
[ ] Build artifact created
[ ] Security checks pass
[ ] Pre-commit hooks configured

TEAM & OPERATIONS
[ ] Team briefed on procedures
[ ] On-call team activated
[ ] Communication channel ready
[ ] Monitoring dashboards available
[ ] Alerts tested and working

DECISION
[ ] All infrastructure checks PASS
[ ] All code checks PASS
[ ] All team checks PASS
[ ] Go/No-Go: GO (proceed to canary)
```

#### 1.5.2 No-Go Triggers
Stop deployment if:
- ❌ Any infrastructure check fails
- ❌ Test pass rate <98%
- ❌ Build fails
- ❌ On-call team not ready
- ❌ Monitoring not functional
- ❌ Critical blockers identified

---

## CANARY DEPLOYMENT PHASE

**Duration**: 1-2 hours
**Owner**: DevOps Team (Deployment Lead)
**Gate**: Must meet success criteria before full rollout

### Phase 2.1: Canary Environment Setup

**Objective**: Deploy to 10% of traffic (canary environment)

#### 2.1.1 Staging Validation
```bash
# Create isolated staging environment with new code
# Copy artifact to staging
cp dist/cohezion-*.tar.gz /staging/deployment/

# Extract in staging
cd /staging/deployment/
tar -xzf cohezion-*.tar.gz

# Install dependencies
cd cohezion-*/
uv sync

# Run basic smoke tests
uv run pytest tests/compound/test_executor.py -v

# Expected: Core executor tests pass
```

#### 2.1.2 Configuration Deploy
```bash
# Copy production configuration to staging
# (using environment variables or config files)

# For SurrealDB
export SURREAL_DB_HOST=localhost
export SURREAL_DB_PORT=8000

# For Ollama
export OLLAMA_HOST=http://localhost:11434

# For cache (if Redis)
export REDIS_HOST=localhost
export REDIS_PORT=6379

# Verify configuration
python3 << 'EOF'
import os
from cohezion.core.config_templates import load_cohezion_config

config = load_cohezion_config()
print(f"Database: {config.surreal_host}:{config.surreal_port}")
print(f"Ollama: {config.ollama_host}")
print("Configuration loaded successfully")
EOF
```

#### 2.1.3 Service Start (Canary)
```bash
# Start Cohezion service in staging (canary)
cd /staging/deployment/cohezion-*/

# For local testing:
uv run uvicorn cohezion.api:app --host 0.0.0.0 --port 8080 &

# For containerized deployment:
docker run -p 8080:8000 cohezion:latest &

# Expected: Service starts on port 8080
# Expected: No startup errors
```

### Phase 2.2: Canary Traffic Routing

**Objective**: Route 10% of traffic to new deployment

#### 2.2.1 Router Configuration
```bash
# For AWS ELB / ALB:
# Create target group pointing to canary (port 8080)
# Set weight to 10% traffic

# For Nginx:
upstream cohezion_stable {
    server prod-1:8000 weight=9;  # 90%
    server prod-2:8000 weight=9;
}
upstream cohezion_canary {
    server canary:8080 weight=2;  # 10%
}

server {
    listen 80;
    location / {
        proxy_pass http://cohezion_stable;
        # Stickiness: route same user to same backend
    }
    location /api/ {
        proxy_pass http://cohezion_canary;  # 10% sampling
    }
}

# For Kubernetes:
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: cohezion
spec:
  hosts:
  - cohezion.example.com
  http:
  - match:
    - uri:
        prefix: /api/
    route:
    - destination:
        host: cohezion-canary
      weight: 10
    - destination:
        host: cohezion-stable
      weight: 90
```

#### 2.2.2 Traffic Verification
```bash
# Verify canary receiving traffic
# Check logs
tail -f /var/log/cohezion/access.log | grep ":8080"

# Expected: Requests appearing in canary logs
# Expected: 10% of total traffic

# Test canary endpoint
curl -H "Host: cohezion.example.com" http://localhost:8080/health
# Expected: 200 OK
```

### Phase 2.3: Canary Monitoring & Metrics

**Objective**: Verify canary deployment is healthy

#### 2.3.1 Real-Time Metrics
```bash
# Monitor every 1 minute for 15 minutes

# ERROR RATE (Target: <0.1%)
curl http://canary:8080/metrics | grep http_requests_total
# Calculate: errors / total_requests
# Expected: <0.1% error rate

# LATENCY (Target: <500ms p99)
curl http://canary:8080/metrics | grep http_request_duration_seconds
# Calculate: 99th percentile
# Expected: <500ms

# CACHE HIT RATE (Target: >90%)
curl http://canary:8080/metrics | grep cache_hits
curl http://canary:8080/metrics | grep cache_requests
# Calculate: hits / total_requests
# Expected: >90%

# AUTHENTICATION (Target: 100% success)
curl http://canary:8080/metrics | grep auth_success_total
# Expected: 100% of auth attempts succeed

# DATABASE CONNECTIVITY (Target: No errors)
curl http://canary:8080/metrics | grep surreal_connection_errors
# Expected: 0 errors
```

#### 2.3.2 Log Analysis
```bash
# Check for error logs
tail -n 100 /var/log/cohezion/canary-error.log

# Expected: No critical errors
# Expected: Only expected warnings

# Check security logs
tail -n 50 /var/log/cohezion/canary-security.log

# Expected: No security incidents
# Expected: Audit trail flowing correctly
```

#### 2.3.3 Business Metrics
```bash
# API response quality
# - Requests completing: should match pre-deployment baseline
# - Response times: within ±10% of baseline
# - Success rates: >99.9%

# User experience
# - Any reported issues? No
# - Performance complaints? No
# - Functionality working? Yes
```

### Phase 2.4: Canary Success Criteria

**All must pass before proceeding to full rollout**

```
CANARY SUCCESS CRITERIA
═════════════════════════════════════════════════════════

ERROR RATE
[ ] <0.1% error rate
[ ] No spike in 5xx responses
[ ] No spike in 4xx responses
[ ] No unhandled exceptions

PERFORMANCE
[ ] Latency <500ms p99
[ ] Latency within ±10% of baseline
[ ] No performance regression

CACHE
[ ] Hit rate >90%
[ ] No cache invalidation issues
[ ] Metrics accurate

AUTHENTICATION & SECURITY
[ ] 100% auth success rate
[ ] Zero security incidents
[ ] Audit logs flowing
[ ] No credential leakage

SYSTEM HEALTH
[ ] Database connections stable
[ ] Ollama service responding
[ ] Memory usage normal (<2GB)
[ ] CPU usage normal (<50%)

EXTERNAL SERVICES
[ ] Redis accessible (if used)
[ ] All integrations responding
[ ] No downstream failures

BUSINESS METRICS
[ ] User reports: None critical
[ ] Functionality: All working
[ ] Performance: Acceptable
[ ] User satisfaction: Good

DECISION
[ ] All metrics PASS
[ ] All checks PASS
[ ] Go/No-Go: GO (proceed to full rollout)
```

### Phase 2.5: Canary Decision Gate

**Decision Point**: Continue to full rollout or rollback?

#### 2.5.1 Pass Criteria
```
PASS: If all success criteria met, proceed to full rollout
```

#### 2.5.2 Fail Criteria
```
FAIL / ROLLBACK: If ANY of the following occur:
- Error rate ≥0.1%
- Latency >500ms p99
- Cache hit rate <90%
- Auth failures >0%
- Security incidents detected
- Database connectivity issues
- Critical user reports
```

If FAIL:
→ See [Rollback Procedures](#rollback-procedures)

---

## FULL PRODUCTION ROLLOUT

**Duration**: ~30 minutes
**Owner**: DevOps Lead
**Gate**: All canary criteria passed

### Phase 3.1: Final Verification

**Objective**: Confirm canary metrics stable before full rollout

#### 3.1.1 Metrics Snapshot
```bash
# Capture final canary metrics
# Store baseline for comparison

TIMESTAMP=$(date +%s)
curl http://canary:8080/metrics > metrics-before-rollout-${TIMESTAMP}.txt

# Expected: All metrics within targets
# Error rate: <0.1%
# Latency p99: <500ms
# Cache hit: >90%
```

#### 3.1.2 Team Confirmation
```
FULL ROLLOUT CONFIRMATION
═════════════════════════════════════════════════════════

[ ] Deployment Lead: Canary metrics verified
[ ] QA Lead: All tests passed
[ ] Security Lead: No security incidents
[ ] Operations Lead: Team ready
[ ] Decision: PROCEED TO FULL ROLLOUT

Authorized By: ___________________  Date: _________
```

### Phase 3.2: Traffic Shift to New Version

**Objective**: Shift 100% of traffic to new deployment

#### 3.2.1 Blue-Green Deployment (Recommended)
```bash
# If using Blue-Green pattern:

# Current state:
# - Blue (old): Running, receiving 100% traffic
# - Green (new): Canary, receiving 10% traffic

# Step 1: Shift all traffic to Green
# (This shifts remaining 90% from Blue to Green)

# AWS ALB example:
aws elbv2 modify-target-group-attributes \
  --target-group-arn arn:aws:elasticloadbalancing:...:targetgroup/cohezion-new/... \
  --attributes Key=deregistration_delay.timeout_seconds,Value=0

aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:...:listener/... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/cohezion-new/...

# Kubernetes example:
kubectl patch service cohezion --patch '{"spec":{"selector":{"version":"v2"}}}'

# Nginx example:
# Shift weight: cohezion_canary 100%, cohezion_stable 0%
# Reload: nginx -s reload
```

#### 3.2.2 Gradual Rollout (Alternative)
```bash
# If gradual shift preferred:

# Minute 1: 25% traffic to new
# Minute 5: 50% traffic to new
# Minute 10: 75% traffic to new
# Minute 15: 100% traffic to new

# Monitor metrics at each step
# If any metric degrades, rollback immediately
```

#### 3.2.3 Old Version Status
```bash
# After traffic fully shifted to new version:

# Option A: Keep old version running (for quick rollback)
# Status: Idle, ready to receive traffic if needed
# Duration: Keep for 24 hours

# Option B: Scale down old version
# Status: Stopped, can be restarted if needed
# Duration: After 24h stable monitoring

# Recommended: Option A (safer rollback)
```

### Phase 3.3: Full Rollout Verification

**Objective**: Verify all traffic on new version is healthy

#### 3.3.1 Real-Time Monitoring
```bash
# First 5 minutes: Monitor every 30 seconds
# Next 10 minutes: Monitor every 1 minute
# Next 15 minutes: Monitor every 5 minutes

# Same metrics as canary:
ERROR_RATE=$(curl -s http://new-version:8000/metrics | grep http_requests_total)
LATENCY=$(curl -s http://new-version:8000/metrics | grep http_request_duration_seconds)
CACHE_HIT=$(curl -s http://new-version:8000/metrics | grep cache_hits)

echo "Error Rate: <0.1% ?"
echo "Latency p99: <500ms ?"
echo "Cache Hit: >90% ?"
```

#### 3.3.2 User Impact Check
```bash
# Monitor user-facing metrics
# - Page load times
# - API response times
# - Error messages from users
# - Support tickets spike?

# Expected: No spike in issues
# Expected: Metrics align with new version
```

#### 3.3.3 System Health
```bash
# Verify new version stability

# Memory usage
docker stats cohezion-new | grep MEMORY
# Expected: <2GB

# CPU usage
top -p $(pgrep -f cohezion) | grep %CPU
# Expected: <50%

# Disk I/O
iostat 1 5 | grep sda
# Expected: Normal operation

# Network
netstat -an | grep ESTABLISHED | wc -l
# Expected: Reasonable number of connections
```

### Phase 3.4: Full Rollout Success Gate

```
FULL ROLLOUT SUCCESS CRITERIA
═════════════════════════════════════════════════════════

TRAFFIC & ROUTING
[ ] 100% traffic routed to new version
[ ] All requests reaching new deployment
[ ] No requests to old version

SYSTEM HEALTH
[ ] Error rate <0.1%
[ ] Latency <500ms p99
[ ] Cache hit rate >90%
[ ] CPU <50%, Memory <2GB

USER EXPERIENCE
[ ] No reports of issues
[ ] Performance acceptable
[ ] Functionality working
[ ] Zero security incidents

MONITORING
[ ] All metrics flowing
[ ] Alerts testing successfully
[ ] Dashboards updating
[ ] Logs aggregating

DECISION
[ ] All checks PASS
[ ] Ready for 7-day monitoring

AUTHORIZED BY: ___________________  TIME: __________
```

---

## POST-DEPLOYMENT MONITORING

**Duration**: 7 days (continuous)
**Owner**: DevOps Team (Monitoring Lead)
**Goal**: Verify stability, establish baseline, identify issues

### Phase 4.1: Day 1 - Intensive Monitoring

**Objective**: First 24 hours of close monitoring

#### 4.1.1 Hourly Metric Snapshots
```bash
# Every hour for 24 hours:

for i in {1..24}; do
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)

  # Capture metrics
  curl -s http://new-version:8000/metrics > metrics-day1-hour${i}-${TIMESTAMP}.txt

  # Check error rate
  ERROR_RATE=$(grep 'http_requests_total.*status="5"' metrics-day1-hour${i}-${TIMESTAMP}.txt)

  # Check latency
  LATENCY=$(grep 'http_request_duration_seconds' metrics-day1-hour${i}-${TIMESTAMP}.txt | tail -1)

  # Check cache
  CACHE=$(grep 'cache_hits' metrics-day1-hour${i}-${TIMESTAMP}.txt)

  echo "Hour ${i}: Error Rate OK? Latency OK? Cache OK?"
  sleep 3600
done
```

#### 4.1.2 Alert Monitoring
```bash
# Monitor alerts every 15 minutes
# Have on-call team standing by

# If any alert fires:
# 1. Investigate immediately
# 2. Check if expected
# 3. If unexpected, check metrics
# 4. Consider rollback if critical

# Expected alerts: None (or only expected ones)
```

#### 4.1.3 User Experience Monitoring
```bash
# Monitor support channels
# Monitor error tracking (Sentry/DataDog)
# Monitor user feedback

# Expected: No spike in issues
# Expected: Positive feedback
# Expected: Performance good
```

### Phase 4.2: Days 2-7 - Standard Monitoring

**Objective**: Monitor for any delayed issues

#### 4.2.1 Daily Metric Review
```bash
# Daily (at consistent time):

# 1. Review error logs
tail -n 500 /var/log/cohezion/production-error.log | tail -n 100
# Expected: No new errors, same rate as before

# 2. Check performance metrics
# - Error rate: <0.1%
# - Latency p99: <500ms (±10% of baseline)
# - Cache hit: >95% (higher than canary)
# - CPU: <50%
# - Memory: <2GB

# 3. Verify database health
# - Connection count stable
# - Query performance unchanged
# - No slow queries

# 4. Check integrations
# - Ollama: Responding normally
# - Redis: Accessible and responsive
# - Any external APIs: All working
```

#### 4.2.2 Weekly Trend Analysis
```bash
# End of day 7, analyze trends:

# Performance improvement?
# Error rate improvement?
# User satisfaction improvement?
# Cost metrics as expected?

# Create summary report with:
# - Before vs. After metrics
# - Any issues encountered
# - Learnings and recommendations
# - Performance baselines
```

### Phase 4.3: Success Baseline Establishment

**Objective**: Lock in performance baselines

#### 4.3.1 Baseline Metrics
```
PERFORMANCE BASELINE (After 7 days)
═════════════════════════════════════════════════════════

Error Rate:                 ____%  (target: <0.1%)
Latency p99:                ___ms  (target: <500ms)
Cache Hit Rate:             ____%  (target: >95%)
CPU Usage:                  ___%   (target: <50%)
Memory Usage:               __MB   (target: <2GB)
Database Connections:       ____   (stable)
Ollama Response Time:       __ms   (stable)
User Satisfaction:          Good
Cost per Request:           $____  (vs baseline)

All metrics within targets: YES / NO
Ready for 30-day monitoring: YES / NO
```

#### 4.3.2 Operational Playbooks
```bash
# Document for operations team:

# How to respond to high error rate?
# → Check Ollama service health
# → Check database connections
# → Check recent code changes

# How to respond to high latency?
# → Check cache hit rate
# → Check database performance
# → Consider scaling

# How to respond to authentication issues?
# → Check API key validity
# → Check guardrail pipeline
# → Verify TLS configuration

# Etc.
```

### Phase 4.4: Day 7 Approval Gate

```
7-DAY MONITORING COMPLETION
═════════════════════════════════════════════════════════

STABILITY
[ ] Error rate <0.1% (all 7 days)
[ ] Latency <500ms p99 (all 7 days)
[ ] Zero critical incidents
[ ] Zero unplanned rollbacks

PERFORMANCE
[ ] Cache hit rate >95%
[ ] CPU <50%, Memory <2GB
[ ] Database healthy
[ ] All integrations responsive

USER EXPERIENCE
[ ] No critical user issues
[ ] Positive feedback
[ ] Functionality stable
[ ] Performance acceptable

COMPLIANCE
[ ] Audit logs complete
[ ] Security events normal
[ ] Zero security incidents
[ ] Compliance requirements met

APPROVAL
[ ] Deployment Lead: Approves ___________________
[ ] Operations Lead: Approves ___________________
[ ] Security Lead: Approves ___________________

STATUS: APPROVED FOR LONG-TERM OPERATION ✅
DATE: _________  TIME: __________
```

---

## TROUBLESHOOTING GUIDE

### Issue 1: High Error Rate (>0.1%)

**Symptom**: Error rate trending >0.1%

**Diagnosis Steps**:
```bash
# 1. Check error type
curl http://new-version:8000/metrics | grep http_requests_total

# 2. Check error logs
tail -n 100 /var/log/cohezion/error.log | grep -i error

# 3. Check specific error types
grep "500\|502\|503" /var/log/cohezion/error.log | tail -20
grep "Timeout\|Connection" /var/log/cohezion/error.log | tail -20
grep "Auth\|Permission" /var/log/cohezion/error.log | tail -20
```

**Common Causes**:
1. **Database Connection Issue**
   - Check: `curl -s http://surreal:8000/`
   - Fix: Restart SurrealDB, check network connectivity

2. **Ollama Service Issue**
   - Check: `curl http://localhost:11434/api/tags`
   - Fix: Restart Ollama, check memory available

3. **Authentication Failure**
   - Check: Look for "APIKeyAuth rejected" in logs
   - Fix: Verify API keys, check header format

4. **Code Issue**
   - Check: Recent code changes
   - Fix: Check recent commits, possibly rollback

**Resolution**:
```bash
# If issue is temporary (network glitch):
# Wait 5 minutes, monitor error rate trending down
# No action needed

# If issue persists:
# 1. Alert on-call team
# 2. Check root cause
# 3. If cannot resolve in 15 min, consider rollback
# 4. Rollback if error rate spike significant
```

### Issue 2: High Latency (>500ms p99)

**Symptom**: API responses slow

**Diagnosis Steps**:
```bash
# 1. Check cache hit rate
curl -s http://new-version:8000/metrics | grep cache_hits
# If <90%, cache issue

# 2. Check database latency
curl -s http://new-version:8000/metrics | grep surreal_request_duration
# If high, database slow

# 3. Check Ollama response time
curl -s http://new-version:8000/metrics | grep ollama_request_duration
# If high, model inference slow

# 4. Check resource usage
free -h  # Memory
top -1 | head  # CPU
```

**Common Causes**:
1. **Low Cache Hit Rate**
   - Check: Cache warming on startup
   - Fix: Restart service, allow cache to populate

2. **Database Slow**
   - Check: Database CPU, memory, disk I/O
   - Fix: Optimize queries, add indexes, scale database

3. **Model Inference Slow**
   - Check: Ollama model size, hardware
   - Fix: Use smaller model (phi3:mini), increase memory

4. **Memory Pressure**
   - Check: Container memory limit vs actual usage
   - Fix: Increase memory allocation, reduce cache size

**Resolution**:
```bash
# If latency spike temporary:
# Monitor for 5 minutes
# If trending down, no action needed

# If latency sustained:
# Check cache, database, Ollama in order
# Scale resources if needed
# If cannot resolve in 30 min, consider rollback
```

### Issue 3: Cache Hit Rate Low (<90%)

**Symptom**: Cache not effective

**Diagnosis Steps**:
```bash
# 1. Verify cache is running
ps aux | grep -i redis  # If using Redis
curl http://localhost:6379/  # Test Redis

# 2. Check cache metrics
curl -s http://new-version:8000/metrics | grep cache
# Look for cache_size, cache_hits, cache_misses

# 3. Check semantic cache initialization
python3 << 'EOF'
from cohezion.cache.semantic_cache import SemanticCache
cache = SemanticCache()
print(f"Cache initialized: {cache is not None}")
print(f"L1 (hash) size: {cache._l1_cache_size if hasattr(cache, '_l1_cache_size') else 'N/A'}")
print(f"L2 (semantic) size: {cache._l2_cache_size if hasattr(cache, '_l2_cache_size') else 'N/A'}")
EOF
```

**Common Causes**:
1. **Cache Not Warmed**
   - Fix: Restart service, let cache populate from typical queries

2. **Cache TTL Too Short**
   - Check: Configuration
   - Fix: Increase TTL for stable data

3. **Redis Not Available**
   - Check: `redis-cli ping`
   - Fix: Restart Redis, verify network access

4. **Cache Configuration Issue**
   - Fix: Verify REDIS_HOST, REDIS_PORT in environment

**Resolution**:
```bash
# Monitor cache hit rate over next hour
# Should improve as cache populates
# No action usually needed (self-healing)

# If still <80% after 1 hour:
# Check Redis availability
# Consider increasing cache size or TTL
```

### Issue 4: Authentication Failures

**Symptom**: Users getting auth errors

**Diagnosis Steps**:
```bash
# 1. Check auth middleware logs
grep -i "auth\|401\|403" /var/log/cohezion/error.log | tail -20

# 2. Verify API keys
# Check if keys exist in system
grep -r "API_KEY" /etc/cohezion/

# 3. Test authentication
curl -H "Authorization: Bearer VALID_KEY" http://new-version:8000/health
# Expected: 200 OK

curl -H "Authorization: Bearer INVALID_KEY" http://new-version:8000/health
# Expected: 401 Unauthorized
```

**Common Causes**:
1. **API Keys Not Configured**
   - Fix: Load API keys into environment, restart service

2. **Key Format Issue**
   - Check: Header format in logs
   - Fix: Verify client is sending `Authorization: Bearer <key>`

3. **TLS Certificate Issue**
   - Check: Verify certificate validity
   - Fix: Update certificate if expired

4. **Auth Middleware Bug**
   - Check: Recent code changes
   - Fix: Review changes, possibly rollback

**Resolution**:
```bash
# If few auth failures (<5%):
# Normal - some requests may be malformed
# Monitor, no action

# If widespread auth failures:
# Check API keys configured
# Verify client library updated
# May need rollback
```

### Issue 5: Database Connectivity Issues

**Symptom**: Database connection errors in logs

**Diagnosis Steps**:
```bash
# 1. Test SurrealDB connectivity
curl http://localhost:8000/

# 2. Check connection status
netstat -an | grep 8000
# Expected: Multiple connections

# 3. Check database status
surreal info
# Or: curl http://localhost:8000/api/version

# 4. Verify namespace and database exist
python3 << 'EOF'
import asyncio
from surrealdb import Surreal

async def test():
    async with Surreal('ws://localhost:8000/rpc') as db:
        await db.use('cohezion', 'core')
        tables = await db.query('SELECT * FROM meta::tables')
        print(f"Tables: {len(tables)}")

asyncio.run(test())
EOF
```

**Common Causes**:
1. **SurrealDB Service Down**
   - Fix: Restart SurrealDB service

2. **Network Connectivity Issue**
   - Check: `ping localhost`, `netstat -an | grep 8000`
   - Fix: Check firewall rules, network configuration

3. **Database Credentials Wrong**
   - Fix: Verify username/password in configuration

4. **Connection Pool Exhausted**
   - Check: Number of connections
   - Fix: Increase pool size or reduce concurrent users

**Resolution**:
```bash
# If temporary (single failed connection):
# Auto-retry will reconnect
# No action needed

# If persistent:
# Check SurrealDB status immediately
# If SurrealDB down, restart it
# If still failing, investigate network
# If cannot resolve in 5 min, consider rollback
```

---

## ROLLBACK PROCEDURES

### When to Rollback

**Rollback immediately if**:
- Error rate >1% (or >10x baseline)
- Data corruption detected
- Security incident detected
- Service completely down
- Cannot diagnose and fix in 15 minutes

**Rollback after investigation if**:
- Widespread auth failures
- Critical functionality broken
- Cannot reach success criteria

**Do NOT rollback**:
- Minor latency increase
- Single feature issue
- Non-critical system problem
- Transient errors

### Rollback Procedure (Blue-Green)

**Duration**: 5-15 minutes

#### Step 1: Decision & Authorization
```bash
# Decision: Who makes the call?
# → Deployment Lead makes rollback decision
# → Notify all stakeholders immediately

echo "ROLLBACK INITIATED: $(date)" | tee /var/log/rollback.log
echo "Reason: [specific reason]" >> /var/log/rollback.log
```

#### Step 2: Shift Traffic Back to Old Version
```bash
# AWS ALB example:
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:...:listener/... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/cohezion-old/...

# Kubernetes example:
kubectl patch service cohezion --patch '{"spec":{"selector":{"version":"v1"}}}'

# Nginx example:
# Shift weight back to old version, reload

echo "Traffic shifted back to v1 (old version): $(date)" >> /var/log/rollback.log
```

#### Step 3: Verify Old Version Stable
```bash
# Wait 2 minutes for traffic to settle
sleep 120

# Check metrics
curl -s http://old-version:8000/metrics | head -20
ERROR_RATE=$(curl -s http://old-version:8000/metrics | grep http_requests_total)
LATENCY=$(curl -s http://old-version:8000/metrics | grep http_request_duration_seconds)

# Expected: Back to pre-deployment normal
# Error rate: <0.1%
# Latency: <500ms p99

echo "Verification complete: $(date)" >> /var/log/rollback.log
```

#### Step 4: Notify Team
```bash
# Immediately notify:
# - Deployment Lead
# - Operations Team
# - Security Team
# - Product Team
# - Customers (if applicable)

echo "ROLLBACK COMPLETE: $(date)" >> /var/log/rollback.log
echo "Old version (v1) fully restored" >> /var/log/rollback.log
```

### Rollback Procedure (Canary Phase)

If rolling back during canary:

```bash
# Much simpler - just shift all traffic away from canary

# Step 1: Stop canary deployment
docker stop cohezion-canary
# OR
kubectl delete deployment cohezion-canary

# Step 2: Verify stable version healthy
curl -s http://stable:8000/health
# Expected: 200 OK

# Step 3: Monitor metrics
# Should show normal operation

# Step 4: Cleanup canary environment
rm -rf /staging/deployment/

echo "Canary rollback complete: $(date)" >> /var/log/rollback.log
```

### Post-Rollback Analysis

```bash
# 1. Preserve logs and metrics
cp /var/log/cohezion/* /var/log/rollback-analysis/

# 2. Create RCA (Root Cause Analysis)
# What went wrong?
# Why wasn't it caught in canary?
# What's the fix?

# 3. Plan fix and re-test
# - Fix the issue in code
# - Thoroughly test before next deployment
# - Consider additional tests

# 4. Schedule re-deployment
# After fix is verified and tested
```

---

## SUCCESS CRITERIA

### Canary Phase Success
```
✅ Error rate <0.1%
✅ Latency <500ms p99
✅ Cache hit rate >90%
✅ Auth success 100%
✅ No security incidents
✅ Database stable
✅ Ollama responsive
✅ All team checks pass
```

### Full Rollout Success
```
✅ 100% traffic on new version
✅ All canary metrics continue to pass
✅ No regression from canary
✅ User feedback positive
✅ Zero critical issues
✅ Ready for 7-day monitoring
```

### 7-Day Monitoring Success
```
✅ All metrics within targets (all 7 days)
✅ Error rate <0.1% consistent
✅ Latency <500ms p99 consistent
✅ Cache hit rate >95%
✅ Zero critical incidents
✅ Zero security incidents
✅ User satisfaction positive
✅ Baselines established
✅ Ready for long-term operation
```

---

## CONFIGURATION REFERENCE

### Environment Variables
```bash
# SurrealDB
SURREAL_DB_HOST=localhost
SURREAL_DB_PORT=8000
SURREAL_DB_USER=root
SURREAL_DB_PASS=root

# Ollama
OLLAMA_HOST=http://localhost:11434

# Redis (if used)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
API_KEY_HEADER=Authorization
API_KEY_PREFIX=Bearer

# Performance
CACHE_TTL=3600
CACHE_SIZE=1000
POOL_SIZE=10
```

### Configuration Files
```
src/cohezion/core/config_templates.py      # Configuration reference
src/cohezion/security/guardrail_pipeline.py # Security config
src/cohezion/cache/semantic_cache.py        # Cache config
.env.example                                # Example environment
```

---

## Emergency Contacts

**Deployment Issues**: DevOps Lead
**Security Issues**: Security Lead
**Performance Issues**: SRE/Performance Lead
**Application Errors**: Engineering Lead
**Escalation**: Director of Engineering

---

**End of Deployment Runbook**

This runbook is your operational guide. Follow it step-by-step, and deployment will be successful.

**Last Updated**: February 9, 2026
**Version**: 1.0
**Status**: Production Ready

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
