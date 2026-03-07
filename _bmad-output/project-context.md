---
project_name: 'concurrent-discovering-bubble'
user_name: 'Mike-anderson'
date: '2026-03-07T19:46:00Z'
sections_completed:
  - technology_stack
  - language_rules
  - framework_rules
  - testing_rules
  - code_quality_rules
  - workflow_rules
  - dont_miss_rules
existing_patterns_found: 12
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

_Generated by BMAD - 2026-03-07_
