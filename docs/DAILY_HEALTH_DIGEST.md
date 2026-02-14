# Daily Platform Health Digest

## Overview

The Daily Platform Health Digest provides Charter-aligned platform health monitoring with HIHO stability scoring and EDL routing for critical issues.

## Architecture

### 3-Layer Design

1. **Layer 1: Health Data Collection**
   - Repository metrics (size, large files, pack efficiency)
   - Test suite metrics (pass rate, total/failing tests)
   - Dependency metrics (outdated, vulnerable packages)
   - CI/CD metrics (build status, failure rates)
   - Coherence metrics (HIHO stability, internal/external alignment)

2. **Layer 2: Charter-Aligned Scoring**
   - Formula: `50% HIHO stability + 25% metrics health + 25% trend improvement`
   - HIHO repository range: 4-8GB (6GB ± 2GB)
   - HIHO coherence range: 0.4-0.6 (0.5 perfect)
   - Trend analysis over 7 days (improving vs declining)

3. **Layer 3: Action Routing**
   - Observable AI for recommendations
   - EDL routing for critical issues (score <0.5 or critical checks)
   - Journey logging for health assessment history

## Charter Compliance

### HIHO Stability (50% weight)

**Repository HIHO**:
- Target: 6GB
- Range: 4-8GB (HIHO stable)
- Below 4GB: May indicate missing data
- Above 8GB: Approaching cleanup threshold
- Above 10GB: Critical, requires immediate remediation

**Coherence HIHO**:
- Target: 0.5 (maximum stability)
- Range: 0.4-0.6 (HIHO stable)
- Outside range: System diverging from balanced state

### Metrics Health (25% weight)

**Health Checks**:
- Repository size vs thresholds
- Large file count (>1MB in history)
- Pack efficiency (loose objects ratio)
- Test pass rate (target: ≥95%)
- Dependency health (no vulnerabilities)
- CI/CD failure rate (target: <10%)

**Status Categories**:
- ✅ **HEALTHY**: All metrics within acceptable range
- ⚠️  **WARNING**: Some metrics approaching thresholds
- ❌ **CRITICAL**: One or more metrics exceeding limits

### Trend Improvement (25% weight)

**7-Day Trend Analysis**:
- Positive trend: Health improving over time
- Neutral trend: Stable health
- Negative trend: Health declining, investigate causes

## Usage

### Basic Usage

```python
from cohezion.platform.daily_health_digest import get_daily_health_digest

async def check_health():
    digest = get_daily_health_digest()

    # Generate comprehensive health assessment
    result = await digest.generate_digest()

    # Display formatted digest
    print(digest.format_digest_terminal(result))

    # Route critical issues through EDL if needed
    if result.requires_edl_review:
        await digest.route_critical_issues_to_edl(result)
```

### Command-Line Usage

```bash
# Run example script
uv run python scripts/examples/daily_health_digest_example.py

# Schedule as daily cron job (2am UTC)
0 2 * * * cd /path/to/cohezion && uv run python -c "import asyncio; from cohezion.platform.daily_health_digest import get_daily_health_digest; asyncio.run(get_daily_health_digest().generate_digest())"
```

### Integration with Workflows

```python
from cohezion.platform.daily_health_digest import get_daily_health_digest
from cohezion.platform.journey_logger import get_journey_logger

async def daily_maintenance():
    """Daily maintenance workflow with health monitoring."""

    logger = get_journey_logger()
    digest = get_daily_health_digest()

    # Start maintenance journey
    journey_id = await logger.start_journey(
        journey_type="maintenance",
        context="Daily platform maintenance with health check"
    )

    # Generate health digest
    result = await digest.generate_digest()

    # Log health status as decision
    await logger.log_decision(
        journey_id=journey_id,
        decision=f"Health status: {result.overall_status.value}",
        rationale=f"Score: {result.overall_health_score:.3f}, HIHO stable: {result.hiho_stable}"
    )

    # Act on recommendations
    for rec in result.recommendations:
        if "CRITICAL" in rec:
            # Execute critical remediation
            await logger.log_decision(
                journey_id=journey_id,
                decision="Execute critical remediation",
                rationale=rec
            )

    # Complete journey
    await logger.complete_journey(
        journey_id=journey_id,
        outcome=f"Maintenance complete: {result.overall_status.value}",
        context_end=f"Final score: {result.overall_health_score:.3f}"
    )
```

## Health Metrics Reference

### Repository Metrics

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Size | <6GB | 6-10GB | >10GB |
| Large Files | <20 | 20-50 | >50 |
| Pack Efficiency | >70% | 50-70% | <50% |

### Test Metrics

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Pass Rate | ≥95% | 90-95% | <90% |
| Failing Tests | <5% | 5-10% | >10% |

### Dependency Metrics

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Outdated | <5 | 5-10 | >10 |
| Vulnerable | 0 | 0 | >0 |
| Health Score | >0.7 | 0.5-0.7 | <0.5 |

### CI/CD Metrics

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Failure Rate (7d) | <5% | 5-10% | >10% |
| Last Build | Success | Success | Failed |

## Recommendations

The digest automatically generates actionable recommendations based on health checks:

### Repository Recommendations

**Critical Size (>10GB)**:
```bash
# Immediate action required
git tag backup-pre-cleanup
git gc --aggressive --prune=now
git repack -Ad
du -sh .git  # Verify reduction

# If still >10GB, use filter-repo
git filter-repo --path-glob '*.pt' --invert-paths --force
```

**Large Files (>50)**:
```bash
# Migrate to git-lfs
git lfs install
git lfs track "*.pt" "*.pth" "*.ckpt"
git add .gitattributes
git commit -m "chore: Configure git-lfs for large model files"
```

**Poor Pack Efficiency (<50%)**:
```bash
# Run garbage collection
git gc --aggressive --prune=now
git repack -Ad
```

### Test Recommendations

**Low Pass Rate (<90%)**:
```bash
# Investigate failing tests
uv run pytest tests/ -v --tb=short

# Fix test isolation issues
# Check conftest.py for singleton resets
```

### Dependency Recommendations

**Vulnerable Dependencies**:
```bash
# Update immediately
uv sync
uv pip list --outdated

# Check for security advisories
uv pip audit
```

## EDL Routing

When critical issues are detected (score <0.5 or critical health checks), the digest routes decisions through the Expert Domain Lattice:

### Routing Decision Types

- **Security**: Critical vulnerabilities, authentication issues
- **Performance**: Build failures, CI/CD problems
- **Architecture**: Repository structure, large file management

### EDL Expert Streams

- **Engineer**: Implementation and remediation strategies
- **Quantum HW**: Infrastructure and platform issues
- **Architect**: Structural and organizational decisions

### Example EDL Consensus

```python
if digest.requires_edl_review:
    consensus = await digest.route_critical_issues_to_edl(result)

    print(f"EDL Consensus: {consensus.decision}")
    print(f"Coherence: {consensus.coherence:.3f}")
    print(f"Consensus Strength: {consensus.consensus_strength:.3f}")

    if consensus.requires_human_review:
        print("⚠️  Human review required before action")
```

## Persistence

All health digests are persisted to SurrealDB for trending and historical analysis:

```sql
-- Query recent health trends
SELECT
    timestamp,
    overall_health_score,
    overall_status,
    hiho_stable,
    trend_7d
FROM platform_health_digests
ORDER BY timestamp DESC
LIMIT 30;

-- Analyze health decline
SELECT
    timestamp,
    overall_health_score,
    repository_size_gb,
    test_pass_rate
FROM platform_health_digests
WHERE trend_7d < 0
ORDER BY timestamp DESC;
```

## Best Practices

### Daily Monitoring

1. **Schedule daily digest** (2am UTC via cron)
2. **Review recommendations** each morning
3. **Act on critical issues** immediately
4. **Track trends** weekly
5. **Celebrate improvements** when health increases

### Threshold Management

1. **HIHO ranges are Charter-mandated** (do not change)
2. **Warning thresholds** can be tuned per project
3. **Critical thresholds** should remain strict
4. **Trend analysis** requires ≥7 days of data

### Integration Points

1. **CI/CD**: Run digest after each deployment
2. **Pre-commit**: Block commits if health critical
3. **Slack/Discord**: Post digest to team channels
4. **GitHub Issues**: Auto-create issues for critical items

## See Also

- [REPOSITORY_HEALTH_PRIME](../src/cohezion/skills/REPOSITORY_HEALTH_PRIME.md) - Repository governance procedures
- [CoherenceTracker](../src/cohezion/platform/coherence_tracker.py) - HIHO stability measurement
- [JourneyLogger](../src/cohezion/platform/journey_logger.py) - Health journey persistence
- [EDL Router](../src/cohezion/platform/edl_router.py) - Expert domain routing
- [Charter](../.agent/COHEZION_CHARTER.md) - HIHO stability principle
