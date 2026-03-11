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

## Patterns

### Security Guardrails
```python
from cohezion.research.security import CodeChange, ResearchSecurityGuardrails

guardrails = ResearchSecurityGuardrails()
validation = guardrails.validate_change(change)
if not validation.is_valid:
    raise RuntimeError(f"Blocked: {validation.issues}")
```

### API Response Sanitization
```python
import math

def _sanitize_metric(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return value
```

### Session State
```python
@dataclass
class ResearchSession:
    session_id: str = field(default_factory=lambda: datetime.now().isoformat())
    experiments_completed: int = 0
    best_metric: float = field(default_factory=lambda: float("inf"))
```

## Files

- `src/cohezion/research/agent.py` - ResearchAgent (225 lines)
- `src/cohezion/research/config.py` - Configuration (100 lines)
- `src/cohezion/research/security.py` - Guardrails (150 lines)
- `src/cohezion/research/multi_agent.py` - Swarm (200 lines)
- `src/cohezion/research/training.py` - Training (150 lines)
- `src/cohezion/api/research_endpoints.py` - API (312 lines)

## Tests

```bash
pytest tests/research/ -v  # 31 tests, 100% passing
```

## Learnings

See `.claude/skills/research-agent/LEARNINGS_CYCLE_2.md`

## Compound Impact

- 91% code reduction vs karpathy/autoresearch
- Powers Research Squad in compound sessions
- Enables autonomous LLM training optimization
- Full Cohezion ecosystem integration

---

**Version:** 0.2.0  
**Status:** Production Ready  
**Tests:** 31/31 passing (100%)
