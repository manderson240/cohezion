# Skill: research-agent

Autonomous research agent for training optimization with compound executor integration.

## Usage

```python
from cohezion.research import ResearchAgent, ResearchConfig

# Create agent with compound integration
config = ResearchConfig(
    experiment_time_budget=300.0,
    max_experiments=100,
    target_metric="val_bpb",
)
agent = ResearchAgent(config=config)

# Run research session
session = agent.run_session()
print(f"Best metric: {session.best_metric}")
```

## Key Features

- **Compound Integration:** Uses CompoundExecutor for experiment orchestration
- **Security First:** AST-based code validation before execution
- **Multi-Agent:** ResearchSwarm coordinates multiple agents
- **REST API:** Full FastAPI endpoints for external access
- **Production Ready:** Rate limiting, auth, audit logging
- **Cost Optimization:** Token-aware budgeting, auto-downgrade

## Patterns

### Security Guardrails
```python
from cohezion.research.security import CodeChange, ResearchSecurityGuardrails

guardrails = ResearchSecurityGuardrails()
validation = guardrails.validate_change(change)
if not validation.is_valid:
    raise RuntimeError(f"Blocked: {validation.issues}")
```

### Cost Tracking
```python
from cohezion.research.cost_optimization import CostTracker

tracker = CostTracker(budget=CostBudget(max_cost_usd=100.0))
tracker.record_experiment(exp_id, metrics, model)
report = tracker.get_cost_report()
```

### API Response Sanitization
```python
import math

def _sanitize_metric(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return value
```

### Rate Limiting
```python
from cohezion.research.security_api import rate_limit, verify_api_key

@router.post("/start")
@rate_limit(requests_per_minute=60)
async def start_research(
    config: ResearchConfigRequest,
    api_key: dict = Depends(verify_api_key),
):
    ...
```

## Files

### Core (src/cohezion/research/)
- `config.py` (91 lines) - ResearchConfig, ExperimentResult
- `agent.py` (246 lines) - ResearchAgent with CompoundExecutor
- `security.py` (150 lines) - AST validation guardrails
- `multi_agent.py` (200 lines) - ResearchSwarm coordination
- `training.py` (150 lines) - TrainingExecutor
- `checkpoint.py` (200 lines) - Vault persistence
- `flume_integration.py` (250 lines) - VAE hyperparameter search
- `adaptive_refinement.py` (220 lines) - Auto skill improvement
- `security_api.py` (400 lines) - Rate limiting, auth, audit logging
- `cost_optimization.py` (350 lines) - Token budgets, cost tracking

### API (src/cohezion/api/)
- `research_endpoints.py` (312 lines) - 7 REST endpoints

### Tests (tests/research/)
- `test_research_comprehensive.py` (16 tests)
- `test_api_endpoints_tdd.py` (15 tests)
- `test_research_e2e.py` (12 tests)
- `test_research_performance.py` (8 tests)
- `test_cost_optimization.py` (16 tests)
- **Total: 67 tests, 100% passing**

## Tests

```bash
pytest tests/research/ -v  # 67 tests, 100% passing
```

## Learnings

See `.claude/skills/research-agent/LEARNINGS_CYCLE_2.md`

## Production Features

### Security
- Rate limiting (60/min, 1000/hour)
- API key authentication
- Scope-based permissions
- Audit logging
- Input sanitization
- Session ID validation

### Cost Optimization
- Per-experiment cost tracking
- Token-aware budgeting
- Automatic model downgrading
- CSV export for billing
- Usage percentage reporting

### Reliability
- Health check endpoints
- Disk/memory monitoring
- Error recovery
- Checkpoint persistence
- Graceful degradation

## Compound Impact

- 91% code reduction vs karpathy/autoresearch
- Powers Research Squad in compound sessions
- Enables autonomous LLM training optimization
- Full Cohezion ecosystem integration
- Production-ready with security & cost controls

---

**Version:** 0.3.0  
**Status:** Production Ready  
**Tests:** 67/67 passing (100%)
