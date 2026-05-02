<<<<<<< HEAD
# AGENTS.md - Agentic Coding Guidelines for Cohezion

## Build, Lint, and Test Commands

### Quick Reference
```bash
# Format and lint
make format          # Format code with ruff
make lint            # Lint and auto-fix issues
make lint-check      # Check without fixing

# Type checking
make type-check      # Run mypy type checking

# Testing
make test            # Full test suite (~90s)
make test-fast       # Fast unit tests only (<1s each)
uv run pytest tests/compound/ -v       # Single module
uv run pytest tests/test_*.py::test_name -v  # Single test

# Full CI pipeline
make all             # format + lint + lint-tests + type-check + test
```

### Pytest Markers
- `@pytest.mark.fast` - Unit tests under 1s, no live services
- `@pytest.mark.integration` - Requires Ollama/SurrealDB
- `@pytest.mark.mcp` - Requires vault access

### Test Isolation (Critical)
Always mock external services at the source level:
```python
# CORRECT: Mock at source
@patch("cohezion.swarm.compound_client.get_compound_client")

# WRONG: Mock after import
with patch("cohezion.api.compound_client"):  # Import already happened
```

### Singleton Reset Pattern
When tests pass individually but fail in suite, reset singletons in conftest.py:
```python
cohezion.api._vae_trainer = None
cohezion.api._rl_policy = None
logging.getLogger().handlers.clear()
```

---

## Code Style Guidelines

### General
- **Python**: 3.13+
- **Line length**: 100 characters
- **Package manager**: `uv` (never bare pip)
- **Type hints**: Mandatory (mypy --strict compatible)
- **Docstrings**: NumPy-style (document intent, assumptions)
- **Error handling**: Specific exceptions + circuit breakers

### Formatting (ruff)
```bash
ruff format .                    # Format code
ruff check --fix .               # Auto-fix lint issues
```
- Quote style: double quotes
- Indent: spaces
- Line ending: auto

### Import Order (isort via ruff)
1. Standard library (`__future__` first)
2. Third-party packages
3. Local imports (`cohezion`)

```python
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pydantic

from cohezion.flume import VAEEncoder
from cohezion.cache import SemanticCache
```

### Naming Conventions
- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/variables**: `snake_case`
- **Constants**: `SCREAMING_SNAKE_CASE`
- **Private methods**: `_leading_underscore`
- **Type aliases**: `PascalCase` (e.g., `Embedding = np.ndarray`)

### Async/Await (Required)
All I/O must be async with timeouts. No blocking calls in executors:
```python
# CORRECT
async def fetch_data(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await client.get(url)

# WRONG (blocking)
def fetch_data(url: str) -> dict[str, Any]:
    return requests.get(url).json()
```

### Validation (Pydantic)
Use Pydantic at API boundaries for fail-fast validation:
```python
from pydantic import BaseModel, Field

class UserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
```

### Error Handling
- Use specific exception types (not bare `Exception`)
- Add circuit breakers: `cohezion.reliability.get_circuit()`
- Log state transitions: input -> processing -> output

### File Organization
Every `src/cohezion/<dir>` MUST have `__init__.py`:
```
src/cohezion/
  compound/
    __init__.py   # Required!
    executor.py
  cache/
    __init__.py   # Required!
    semantic_cache.py
```

---

## Testing Guidelines

### Test Structure
```python
import pytest
from unittest.mock import AsyncMock, patch

class TestMyFeature:
    """Tests for my_feature."""

    @pytest.mark.fast
    @patch("cohezion.module.function_to_mock")
    async def test_something(self, mock_fn):
        """Test description."""
        mock_fn.return_value = "mocked"
        result = await function_under_test()
        assert result == expected
```

### Fixtures
- Use `conftest.py` for shared fixtures
- Use `tmp_path` for temp files
- Use `@patch` for external dependencies (Ollama, SurrealDB)

### Test Naming
- `test_<method>_<scenario>_<expected>`
- Example: `test_fetch_user_by_id_not_found_raises_error`

---

## Git Workflow

### Branch Naming
- `session-XX-feature` - Feature branches
- `fix/issue-description` - Bug fixes

### Commit Messages (Conventional)
```
feat: add new feature
fix: resolve bug
test: add tests
refactor: restructure code
chore: maintenance
```

### Never
- Force push to main/develop
- Commit secrets to `.env` or `credentials.json`
- Skip pre-commit hooks

---

## Key Learnings from Retrospective

### Compound Session Lifecycle (Critical)
Always use warm-start / clean-shutdown pattern for long-running sessions:
```python
from cohezion.compound.session_manager import CompoundSessionManager

async with CompoundSessionManager() as mgr:
    # Warm-start: cache + metrics loaded automatically
    summary = mgr.start_session(max_cache_entries=256)

    # Alignment gate before execution (HIHO threshold 0.5)
    success, result = await mgr.execute_aligned(
        request="Your task description",
        execute_fn=my_async_function,
        skill_name="auto",
        use_executor=True,  # Full pipeline: inflection + vault + metrics
    )

    # Clean-shutdown: cache + metrics persisted automatically
    end_summary = mgr.end_session()
```

### Alignment Gate (HIHO Stability)
The alignment gate prevents wasted tokens on misaligned requests:
```python
# High coherence (> 0.5) → proceeds
result = mgr.check_alignment("Generate a simple function")
assert result.should_proceed  # True

# Low coherence (< threshold) → blocked
result = mgr.check_alignment("Ambiguous unclear request", threshold=0.5)
if not result.should_proceed:
    # Decompose or escalate instead of executing
    pass
```

### Executor Delegation
When `use_executor=True`, the full pipeline runs:
- get_experience_guidance() - Query vault for similar tasks
- guardrails check - Safety validation
- execute_fn(guidance) - Your task function
- inflection detection - Anomaly detection
- CRITICAL inflection → vault logging
- metrics collection - Token, duration, coherence
- skill refinement trigger - Update skill definitions

### Checkpoint Persistence (Required)
- Primary: Vault storage via MCP (`mcp.vault_write/read/delete`)
- Fallback: Local JSONL in `data/checkpoints/`
- Always delete checkpoint on successful completion

### Cache Persistence Pattern
```python
from cohezion.compound.cache_persistence import CachePersistence, WarmCacheLoader

# On start: warm cache
loader = WarmCacheLoader()
entries_loaded = loader.warm_client(client, max_entries=256)

# On end: persist cache
cp = CachePersistence()
cp.save_cache(client._cache)
```

### Metrics Persistence Pattern
```python
from cohezion.compound.metrics_persistence import MetricsPersistence
from cohezion.compound.metrics import get_collector

collector = get_collector()
mp = MetricsPersistence()
mp.save_snapshot(collector)  # Save at end of session

# Restore at start of session
snapshot = mp.load_latest_snapshot()
if snapshot:
    collector.load_from_snapshot(snapshot)
```

---

## Project-Specific Patterns

### Journey Tracking (Compound Loop)
Track agent actions through 12D universe:
```python
from cohezion.compound.journey_tracker import JourneyTracker

tracker = JourneyTracker()
state = tracker.record_state(
    agent_id="agent-1",
    phase="execution",
    position={"x": 0.5, "y": 0.3},
    coherence=0.85,
)
```

### Request Alignment Analysis
Check coherence before execution:
```python
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer

analyzer = RequestAlignmentAnalyzer()
alignment = analyzer.analyze(request, available_skills, agent_context)
if alignment.coherence < 0.5:
    logger.warning(f"Low alignment: {alignment.issues}")
```

### AgentVerse Integration (Autonomous Benchmarking)

**LLMExecutor** - Execute tasks via Ollama cloud with coherence scoring:
```python
from cohezion.integrations.agentverse import LLMExecutor

executor = LLMExecutor(model="qwen3.5:cloud")
result = await executor.execute_task(task="Write factorial", skill="python_PRIME")
# result.coherence: 0.0-1.0
```

**AutonomousCompoundLoop** - Self-improving benchmark system:
```python
from cohezion.integrations.agentverse import AutonomousCompoundLoop

loop = AutonomousCompoundLoop(
    skills_dir=Path("src/cohezion/skills"),
    mcp_client=mcp_client,
    llm_executor=executor,
    weak_threshold=0.4,
)
skills = loop.discover_skills()
results = await loop.benchmark_all()
# Weak skills auto-refined, results persist to vault
```

**CLI**:
```bash
uv run python -m cohezion.integrations.agentverse.cli autonomous \
    --skills-dir src/cohezion/skills \
    --limit 10 \
    --model qwen3.5:cloud
```

### Cost-Aware Routing
Optimize for cost without sacrificing quality:
```python
from cohezion.swarm.cost_aware_router import CostAwareRouter

router = CostAwareRouter()
model = router.select_model(task_complexity=0.7, budget_remaining=0.50)
```

---

## Directory Quick Reference

| Path | Purpose |
|------|---------|
| `src/cohezion/compound/` | Executor, SkillRefiner, RetrospectionEngine |
| `src/cohezion/integrations/agentverse/` | AgentVerse integration (LLMExecutor, AutonomousCompoundLoop) |
| `src/cohezion/swarm/` | Team orchestration, cost routing |
| `src/cohezion/cache/` | L1/L2/L3 semantic cache |
| `src/cohezion/skills/` | PRIME skill definitions (*.md) |
| `src/cohezion/api/` | FastAPI backend (72 endpoints) |
| `src/cohezion/flume/` | FLUME VAE (256D latent space) |
| `tests/conftest.py` | **CRITICAL**: Singleton reset fixtures |
| `HARDWARE_PROFILE_PRIME.md` | AMD Ryzen AI MAX+ 395 specs |

---

## Key Files to Read First
- `tests/conftest.py` - Test isolation fixtures
- `.agent/CONSTITUTION.md` - Hard constraints
- `.agent/COHEZION_CHARTER.md` - Design theory
- `HARDWARE_PROFILE_PRIME.md` - Hardware truth anchor
=======
# Cohezion AI Agent Context

## Project Overview
Cohezion is an agentic AI framework with universe simulation, compound sessions, and semantic caching.

## Key Directories
- `src/cohezion/compound/` - Executor, SessionManager, SkillRefiner
- `src/cohezion/integrations/agentverse/` - AgentVerse integration
- `src/cohezion/swarm/` - Team orchestration, V-Model engineering
- `src/cohezion/cache/` - L1/L2/L3 semantic cache
- `src/cohezion/skills/` - PRIME skill definitions (*.md)
- `tests/` - Test suite (use `make test-fast` for quick feedback)

## Development Workflow
1. Use `make format` before committing
2. Use `make lint` to check style
3. Use `make type-check` for mypy validation
4. Use `make test-fast` for unit tests (<1s each)

## Critical Patterns
- Always mock external services at source level with `@patch("cohezion.module.function")`
- Reset singletons in tests: `cohezion.api._vae_trainer = None`
- All I/O must be async with timeouts
- Use Pydantic validation at API boundaries

## Autoresearch Mode
When in autoresearch mode:
- Check `autoresearch.md` for session objectives
- Review `autoresearch.ideas.md` for deferred optimizations
- Run experiments with `run_experiment` + `log_experiment`
- Metric: "lower" or "higher" direction matters
- Confidence score appears after 3+ runs

## Extensions Available
- `/diag` - System diagnostics
- `/cost` - Session spending analysis  
- `/oracle <question>` - Get second opinion from another model
- `/plan` - Toggle plan mode for safe exploration
- `/mem <instruction>` - Save instruction to AGENTS.md
- `/usage` - Token/cost dashboard
- `/agent <prompt>` - Spawn side agent (parallel work in tmux + worktree)
- `/agents` - List active side agents
>>>>>>> isolated/session-oom-modularity
