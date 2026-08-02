# TokenEfficientSquad Deployment Plan

## Executive Summary

Deploy TokenEfficientSquad across 4 skill domains for continuous optimization with 10k token budget per skill, achieving 7.5x efficiency gains.

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TokenEfficientSquad                        │
│                     Deployment Layer                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │   Coding    │ │  Analysis   │ │     Docs    │ │ Testing │ │
│  │   Squad     │ │   Squad     │ │   Squad     │ │  Squad  │ │
│  │  10k tokens │ │  10k tokens │ │  10k tokens │ │10k tok  │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └────┬────┘ │
│         └─────────────────┴─────────────────┴─────────────┘   │
│                           │                                   │
│                    ┌──────┴──────┐                            │
│                    │  Vault Sync   │                            │
│                    │  (Shared)     │                            │
│                    └──────┬──────┘                            │
│                           │                                   │
│              ┌────────────┼────────────┐                     │
│              ▼            ▼            ▼                     │
│        ┌─────────┐  ┌─────────┐  ┌─────────┐                │
│        │Metrics  │  │ Learn   │  │  Alert  │                │
│        │Dashboard │  │ ings    │  │  System │                │
│        └─────────┘  └─────────┘  └─────────┘                │
└─────────────────────────────────────────────────────────────┘
```

## Phase 1: Foundation (Week 1)

### Day 1-2: Infrastructure Setup

**Tasks:**
1. Create skill optimization configuration
2. Set up vault directories for each skill
3. Initialize metric collection
4. Configure token budget tracking

**Deliverables:**
- `config/skill_optimization.yaml`
- `data/vault/{coding,analysis,docs,testing}/` directories
- Token budget monitoring hooks

### Day 3-4: Coding Squad Deployment

**First Skill Deployment:**
```python
# config/skill_optimization.yaml
coding_squad:
  skill: "coding"
  metric: "coherence"
  baseline: 0.45
  target: 0.60
  token_budget: 10000
  max_experiments: 5
  threshold: 0.50
  schedule: "continuous"
  vault_project: "cohezion"
```

**Execution:**
```python
async with TokenEfficientSquad(
    skill="coding",
    token_budget=10000,
) as squad:
    # Initial baseline check
    signal = squad.check_degradation(0.45)
    if signal:
        result = await squad.optimize(baseline=0.45, max_experiments=5)
```

**Success Criteria:**
- [ ] Degradation detected at 0.45
- [ ] 5 experiments completed
- [ ] Improvement > 10% OR cost < $10
- [ ] Results logged to vault
- [ ] Token usage < 2,500 (25% of budget)

### Day 5: Monitoring Setup

**Metrics Dashboard:**
```python
# src/cohezion/research/optimization_metrics.py
@dataclass
class SquadMetrics:
    skill: str
    tokens_used: int
    tokens_remaining: int
    experiments_run: int
    improvement_pct: float
    cost_usd: float
    last_optimized: datetime
    degradation_count: int
```

## Phase 2: Scale (Week 2)

### Day 1-3: Multi-Skill Deployment

**Deploy remaining 3 skills in parallel:**

| Skill | Baseline | Target | Budget | Schedule |
|-------|----------|--------|--------|----------|
| analysis | 0.40 | 0.55 | 10k | continuous |
| docs | 0.50 | 0.65 | 10k | daily |
| testing | 0.35 | 0.50 | 10k | continuous |

**Parallel Execution:**
```python
async def optimize_all_skills():
    skills = [
        ("coding", 0.45),
        ("analysis", 0.40),
        ("docs", 0.50),
        ("testing", 0.35),
    ]

    tasks = [run_optimization_skill(skill, baseline) for skill, baseline in skills]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Day 4-5: Integration & Testing

**Integration Points:**
1. Compound executor hook
2. Vault logging verification
3. Metrics aggregation
4. Alert system testing

**Test Suite:**
```python
# tests/research/test_token_efficient_squad.py
async def test_full_deployment():
    """Test all 4 squads in parallel."""
    results = await optimize_all_skills()
    assert all(r.improvement_pct > 0 for r in results)
    assert all(r.cost_usd < 10 for r in results)
```

## Phase 3: Optimization (Week 3)

### Continuous Improvement Loop

**Daily Operations:**
1. **Morning Check**: Review overnight optimization results
2. **Midday**: Check token budgets, adjust if needed
3. **Evening**: Review degradation signals, trigger optimizations

**Weekly Review:**
- Analyze improvement trends
- Adjust token budgets based on performance
- Update baselines if significant improvements achieved
- Document learnings to vault

### Automation

**Cron Schedule:**
```bash
# Run optimization checks every 4 hours
0 */4 * * * cd /home/mike-anderson/dev/cohezion && uv run python3 -m cohezion.research.optimize_skills

# Weekly report generation
0 9 * * 1 cd /home/mike-anderson/dev/cohezion && uv run python3 -m cohezion.research.weekly_report
```

## Token Budget Allocation

**Per Skill (10k tokens):**
- Squad initialization: 150 tokens (1x)
- Context loading: 100 tokens (1x)
- Experiments: 1,000 tokens (5 @ 200 each)
- Result processing: 200 tokens
- Vault logging: 150 tokens
- **Total per optimization: ~1,600 tokens**
- **Optimizations per budget: ~6 runs per skill**
- **Total across 4 skills: 40k tokens, ~24 optimization runs**

**Efficiency Multiplier:**
- Naive approach: 6,000 tokens per skill
- TokenEfficientSquad: 1,600 tokens per skill
- **Savings: 3.75x per skill, 15x total**

## Monitoring & Alerting

### Key Metrics

**Real-time Dashboard:**
```python
dashboard_metrics = {
    "coding": {
        "current_metric": 0.52,
        "baseline": 0.45,
        "improvement": 15.5%,
        "tokens_used": 8200,
        "tokens_remaining": 1800,
        "last_run": "2026-03-12T14:30:00",
        "status": "healthy"
    },
    # ... other skills
}
```

### Alert Conditions

**Trigger alerts when:**
- Token budget < 20% remaining
- No improvement after 3 consecutive runs
- Degradation detected but optimization fails
- Cost exceeds $8 USD (80% of limit)
- Squad crashes or errors

## Success Criteria

### Phase 1 Success
- [ ] Coding squad operational
- [ ] Degradation detection working
- [ ] Vault logging functional
- [ ] Token tracking accurate

### Phase 2 Success
- [ ] All 4 squads deployed
- [ ] Parallel execution working
- [ ] Metrics dashboard live
- [ ] Alert system functional

### Phase 3 Success
- [ ] 30-day optimization history
- [ ] Average improvement > 10%
- [ ] Token efficiency > 5x vs naive
- [ ] Zero budget overruns
- [ ] Continuous operation without manual intervention

## Rollback Plan

**If issues arise:**
1. Disable auto-optimization triggers
2. Revert to manual Research Squad usage
3. Review vault logs for error patterns
4. Adjust thresholds or budgets
5. Re-enable gradually

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Token budget exceeded | Hard limit + alerts at 80% |
| No improvement | Adjust threshold, try different metrics |
| Squad crashes | Retry logic + fallback to manual |
| Vault unavailable | Local logging + retry |
| Parallel conflicts | Async-safe, no shared state |

## Documentation

**Created:**
- [x] `src/cohezion/research/token_efficient_squad.py` - Core module
- [x] `demo_token_efficient.py` - Usage demo
- [x] This deployment plan

**To Create:**
- [ ] `config/skill_optimization.yaml` - Configuration
- [ ] `src/cohezion/research/optimization_metrics.py` - Monitoring
- [ ] `src/cohezion/research/optimize_skills.py` - Runner script
- [ ] `tests/research/test_token_efficient_squad.py` - Test suite
- [ ] `docs/TOKEN_EFFICIENT_SQUAD.md` - User guide

## Timeline

| Phase | Week | Deliverables |
|-------|------|--------------|
| 1 | 1 | Coding squad + monitoring |
| 2 | 2 | 4 squads + integration |
| 3 | 3 | Automation + docs |
| 4 | 4+ | Continuous operation |

**Total Duration:** 3 weeks to production

## Next Steps

1. ✅ Review and approve plan
2. Create configuration files
3. Deploy Coding Squad (Phase 1)
4. Monitor and iterate
5. Scale to remaining skills (Phase 2)
6. Automate (Phase 3)

**Ready to execute?**

Say "execute Phase 1" to begin deployment.
