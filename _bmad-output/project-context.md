---
project_name: 'concurrent-discovering-bubble'
user_name: 'Mike-anderson'
date: '2026-03-09'
sections_completed:
  - technology_stack
  - language_rules
  - framework_rules
  - testing_rules
  - code_quality_rules
  - workflow_rules
  - dont_miss_rules
  - elegant_simplification_patterns
existing_patterns_found: 18
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in the Cohezion project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

**Core Technologies:**
- Python 3.13+
- Package Manager: `uv` (never use bare pip)
- Line Length: 100 characters
- Type Hints: Mandatory (mypy --strict compatible)

**Key Dependencies:**
- FastAPI >=0.104.0 (72+ routes)
- Pydantic >=2.0.0 with Pydantic Settings
- SurrealDB >=0.3.0 (WebSocket)
- Redis >=7.2.1 (TCP caching)
- httpx >=0.25.0 (async HTTP)
- numpy >=1.24.0
- torch >=2.0.0 (optional ML)
- gymnasium >=1.2.3

**Development Tools:**
- ruff >=0.8.0 (format + lint)
- mypy >=1.5.0 (type check)
- pytest >=8.0.0 with pytest-asyncio >=0.23.0
- pytest-cov >=4.1.0

**Build Commands:**
- `make format` - Format code with ruff
- `make lint` - Lint and auto-fix
- `make type-check` - Run mypy
- `make test` - Full test suite
- `make test-fast` - Fast unit tests only (<1s each)
- `make all` - format + lint + type-check + test

---

## Critical Implementation Rules

### Language-Specific Rules

**Import Order (isort via ruff):**
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

**Async/Await (Required):**
- All I/O must be async with timeouts
- No blocking calls in executors

```python
# CORRECT
async def fetch_data(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await client.get(url)

# WRONG (blocking)
def fetch_data(url: str) -> dict[str, Any]:
    return requests.get(url).json()
```

**Naming Conventions:**
- **Modules:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions/variables:** `snake_case`
- **Constants:** `SCREAMING_SNAKE_CASE`
- **Private methods:** `_leading_underscore`
- **Type aliases:** `PascalCase` (e.g., `Embedding = np.ndarray`)

### Framework-Specific Rules

**Pydantic Validation (Required at API boundaries):**
- Use Pydantic at API boundaries for fail-fast validation
- Document intent and assumptions in NumPy-style docstrings

```python
from pydantic import BaseModel, Field

class UserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
```

**Error Handling:**
- Use specific exception types (not bare `Exception`)
- Add circuit breakers: `cohezion.reliability.get_circuit()`
- Log state transitions: input -> processing -> output

**File Organization:**
- Every `src/cohezion/<dir>` MUST have `__init__.py`

```
src/cohezion/
  compound/
    __init__.py   # Required!
    executor.py
  cache/
    __init__.py   # Required!
    semantic_cache.py
```

### Testing Rules

**Pytest Markers:**
- `@pytest.mark.fast` - Unit tests under 1s, no live services
- `@pytest.mark.integration` - Requires Ollama/SurrealDB
- `@pytest.mark.mcp` - Requires vault access

**Test Isolation (Critical):**
- Always mock external services at the source level

```python
# CORRECT: Mock at source
@patch("cohezion.swarm.compound_client.get_compound_client")

# WRONG: Mock after import
with patch("cohezion.api.compound_client"):  # Import already happened
```

**Test Naming:**
- `test_<method>_<scenario>_<expected>`
- Example: `test_fetch_user_by_id_not_found_raises_error`

**Singleton Reset Pattern:**
- When tests pass individually but fail in suite, reset singletons in conftest.py

```python
cohezion.api._vae_trainer = None
cohezion.api._rl_policy = None
logging.getLogger().handlers.clear()
```

### Code Quality & Style Rules

**Linting/Formatting:**
- ruff: line-length 100, quote-style double, indent-style space
- isort: known-first-party = ["cohezion"], lines-after-imports = 2

**ruff Configuration (from pyproject.toml):**
- Target Python: py311
- Enable: E, F, W, I, N, UP, S, B, A, C4, SIM, TCH, RUF
- Per-file ignores for tests: S101, S105, S106 (allow asserts/passwords in tests)

**Type Checking:**
- mypy --strict compatible
- warn_return_any = true
- no_implicit_optional = true
- strict_equality = true

### Development Workflow Rules

**Git Workflow:**
- Branch naming: `session-XX-feature` for features, `fix/issue-description` for bugs
- Commit messages (Conventional): `feat:`, `fix:`, `test:`, `refactor:`, `chore:`
- Never force push to main/develop
- Never skip pre-commit hooks

**Data Directory Lifecycle (P3 Consensus):**
- `data/` is **ephemeral cache**, not source control
- All contents must be regenerable from source code and configuration
- Commands:
  - `make onboard` - regenerates seed data
  - `make clean-data` - removes all generated data
  - `make reset-data` - clean + regenerate

**Security Rules:**
- Never commit secrets to `.env` or `credentials.json`
- Never modify `.agent/CONSTITUTION.md`, `.agent/COHEZION_CHARTER.md`
- Use path traversal protection with canonical path validation

### Critical Don't-Miss Rules

**Compound Session Lifecycle (Critical):**
Always use warm-start / clean-shutdown pattern for long-running sessions:

```python
from cohezion.compound.session_manager import CompoundSessionManager

async with CompoundSessionManager() as mgr:
    summary = mgr.start_session(max_cache_entries=256)
    # ... run compound cycles ...
    result = mgr.end_session()
```

**Checkpoint Persistence (Required):**
- Primary: Vault storage via MCP (`mcp.vault_write/read/delete`)
- Fallback: Local JSONL in `data/checkpoints/`
- Always delete checkpoint on successful completion

**Cache Persistence Pattern:**
```python
from cohezion.compound.cache_persistence import CachePersistence, WarmCacheLoader

# On start: warm cache
loader = WarmCacheLoader()
entries_loaded = loader.warm_client(client, max_entries=256)

# On end: persist cache
cp = CachePersistence()
cp.save_cache(client._cache)
```

**Metrics Persistence Pattern:**
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

**Project-Specific Patterns:**

_Journey Tracking (Compound Loop):_
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

_Cost-Aware Routing:_
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
| `src/cohezion/swarm/` | Team orchestration, cost routing |
| `src/cohezion/cache/` | L1/L2/L3 semantic cache |
| `src/cohezion/skills/` | PRIME skill definitions (*.md) |
| `src/cohezion/api/` | FastAPI backend (72 endpoints) |
| `src/cohezion/flume/` | FLUME VAE (256D latent space) |
| `tests/conftest.py` | **CRITICAL**: Singleton reset fixtures |
| `HARDWARE_PROFILE_PRIME.md` | AMD Ryzen AI MAX+ 395 specs |

---

## Update: Elegant Simplification Patterns (2026-03-09)

### Plugin Architecture (New Critical Pattern)

**Accept optional dependencies as constructor parameters, not god objects:**
- Maximum 4 constructor parameters for core classes
- Use dependency injection for analyzers, persisters, and plugins
- Never create god objects with 15+ optional parameters

```python
# CORRECT: Clean plugin architecture
def __init__(
    self,
    execute_fn: Callable,
    config: ExecutionConfig | None = None,
    analyzer: Callable | None = None,
    persister: Callable | None = None,
):

# WRONG: God object (old CompoundExecutor had 15 parameters)
```

### Unified Data Models

**Consolidate scattered dataclasses into single models.py:**
- Use type aliases for cleaner code: `TaskId = str`, `SessionId = str`
- All core types in one location for consistency
- Reduces imports and circular dependencies

### Backward Compatibility (Required)

**When refactoring, always:**
1. Create `compat.py` module to bridge old → new API
2. Preserve old API while introducing new implementation
3. Archive old code before deletion (in `cohezion-archive/`)
4. Maintain 100% backward compatibility during transition

### Async Test Patterns (Critical)

**Mock async executors properly:**
```python
# CORRECT: Mock returns ExecutionResult
def mock_executor(task, context):
    return ExecutionResult(success=True, output="done")

# WRONG: Mock returns tuple (fails!)
def mock_executor(task, context):
    return ("output", {"tokens": 100})
```

**Always use pytest.mark.asyncio:**
- All async tests need `@pytest.mark.asyncio()` decorator
- Use `AsyncMock` for async dependencies

### Code Simplification Workflow

**When reducing technical debt:**
1. Archive first (never delete immediately)
2. Mine for critical components
3. Create unified replacement (~200 lines vs 1,000+)
4. Add compatibility layer (compat.py)
5. Generate comprehensive tests (aim for 100% pass rate)
6. Validate all functionality preserved
7. Document in project context

**Target Metrics:**
- Minimum 60% code reduction for legacy modules
- Maintain 99%+ test pass rate
- Zero breaking changes (via compat layer)

### Batch Processing Standards

**BatchConfig defaults:**
- `max_batch_size`: 10 (hard limit)
- `optimal_batch_size`: 5 (trigger threshold)
- `max_concurrent`: 4 (semaphore limit)
- Always use `asyncio.Semaphore` for concurrency control

**BatchResult requirements:**
- Calculate `success_rate = successful / total`
- Track `failed_tasks` separately from results
- Support mixed success/failure in single batch

### Analytics Engine Rules

**Analysis priority order:**
1. Quality check (coherence, quality_score)
2. Degradation check (duration > 80% of timeout)
3. Anomaly detection (tokens > 100K, timeout errors)
4. Retry recommendation

**Thresholds:**
- Coherence minimum: 0.5
- Quality score minimum: 0.7
- Duration threshold: 80% of task timeout
- Token anomaly: > 100,000 tokens

### BMAD TEA Workflow Rules

**Disciplined execution:**
- Use step-file architecture (micro-file pattern)
- Always save progress after each step
- Update frontmatter: `stepsCompleted`, `lastStep`, `lastSaved`
- Never skip steps or proceed without user confirmation

### New Simplified Modules

| Module | Original | Simplified | Reduction |
|--------|----------|------------|-----------|
| `compound/core/executor.py` | 1,106 lines | ~200 lines | 82% |
| `compound/core/batch_processor.py` | 648 lines | ~200 lines | 69% |
| `compound/analytics/engine.py` | 2,121 lines | ~200 lines | 91% |
| `swarm/orchestrator.py` | 425 lines | ~150 lines | 65% |
| `mcp/manager.py` | 669 lines | ~200 lines | 70% |
| `security/pipeline.py` | 276 lines | ~200 lines | 28% |

**Status:** All simplified modules tested at 100% pass rate (53/53 tests)

---

_Generated by BMAD - 2026-03-09_
