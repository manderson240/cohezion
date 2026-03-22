---
project_name: 'concurrent-discovering-bubble'
user_name: 'Mike-anderson'
date: '2026-03-12'
status: 'complete'
sections_completed:
  - technology_stack
  - language_rules
  - framework_rules
  - testing_rules
  - code_quality_rules
  - workflow_rules
  - dont_miss_rules
  - elegant_simplification_patterns
  - research_agent_patterns
  - test_isolation_patterns
existing_patterns_found: 22
optimized_for_llm: true
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
| `research/` (autoresearch) | ~5,000 lines | ~1,200 lines | **91%** |

**Status:** All simplified modules tested at 100% pass rate (31/31 research tests)

---

## ResearchAgent Patterns (2026-03-10)

### Module Structure
```
src/cohezion/research/
├── config.py          (100 lines) - ResearchConfig, ExperimentResult
├── agent.py           (225 lines) - ResearchAgent with CompoundExecutor
├── training.py        (150 lines) - TrainingExecutor with PyTorch
├── security.py        (150 lines) - ResearchSecurityGuardrails (AST)
├── multi_agent.py     (200 lines) - ResearchSwarm coordination
└── README.md          (250 lines) - Module documentation
```

**Total:** ~1,200 lines vs karpathy/autoresearch ~5,000 lines = **91% reduction**

### Security-First Pattern (Required)
```python
from cohezion.research.security import CodeChange, ResearchSecurityGuardrails

guardrails = ResearchSecurityGuardrails()
change = CodeChange(
    file_path=train_script,
    old_code="",
    new_code=train_script.read_text(),
    change_type="modify",
)
validation = guardrails.validate_change(change)
if not validation.is_valid:
    raise RuntimeError(f"Guardrail blocked: {validation.issues}")
```

**Security checks:**
- AST parsing before execution
- Forbidden patterns: `import os`, `open(`, `eval(`, `exec(`, `__import__`, `subprocess`, `socket`
- Dangerous operations: `compile()`, `getattr(__builtins__`, `delattr`, `setattr`

### API Response Sanitization (Required)
```python
import math

def _sanitize_metric(value: float | None) -> float | None:
    """Return None for non-finite floats to keep JSON valid."""
    if value is None or not math.isfinite(value):
        return None
    return value

def _sanitize_json(obj: Any) -> Any:
    """Recursively replace non-finite floats with None."""
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json(item) for item in obj]
    return obj
```

**Critical:** FastAPI cannot serialize `inf`, `-inf`, `nan` to JSON. Always sanitize floats.

### ResearchSession Dataclass Pattern
```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ResearchSession:
    """Session state with factory defaults."""
    session_id: str = field(default_factory=lambda: datetime.now().isoformat())
    experiments_completed: int = 0
    best_metric: float = field(default_factory=lambda: float("inf"))
    best_checkpoint: Path | None = None
    active: bool = True
```

**Note:** Use `field(default_factory=...)` for dynamic defaults, not mutable defaults.

### Session Storage Pattern
```python
# In-memory with size limits (production: Redis/SurrealDB)
_MAX_SESSIONS = 50
_active_sessions: dict[str, ResearchAgent] = {}

if len(_active_sessions) >= _MAX_SESSIONS:
    raise HTTPException(status_code=429, detail="Too many active sessions")
```

### CompoundExecutor Integration
```python
from cohezion.compound.core.executor import CompoundExecutor, ExecutionConfig

executor = CompoundExecutor(
    execute_fn=self._run_experiment,
    config=ExecutionConfig(max_retries=1),
)
```

### Test Coverage Standards
- Unit tests: `tests/research/test_research_comprehensive.py` (16 tests)
- API tests: `tests/research/test_api_endpoints_tdd.py` (15 tests)
- **Total: 31 tests, 100% passing**
- Minimum 90% code coverage for new modules

---

## Test Isolation Patterns

### Lazy Import Pattern for Heavy Dependencies

**Problem:** Tests fail on collection due to torch/transformers imports in conftest.py.

**Solution:** Wrap heavy imports in try/except with null safety:

```python
# tests/conftest.py
from types import ModuleType

# Reset FLUME VAE singleton to prevent state pollution across tests
api_module: ModuleType | None = None
try:
    import cohezion.api as api_module
except Exception:
    pass
if api_module is not None and hasattr(api_module, "_vae_trainer"):
    api_module._vae_trainer = None
```

**Why:** Allows tests to collect even when heavy ML dependencies are unavailable or broken.

### Shared Data Directory Fixture

**Problem:** ResearchConfig requires paths within `data/` directory (security fix).

**Solution:** Create reusable fixture in conftest.py:

```python
# tests/conftest.py
import shutil
import uuid

@pytest.fixture
def data_temp_dir() -> Generator[Path, None, None]:
    """Create temp dir under data/ for security compliance."""
    test_dir = Path("data") / "test_runs" / uuid.uuid4().hex[:8]
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)

# In tests:
def test_with_path(data_temp_dir):
    config = ResearchConfig(
        experiment_log=data_temp_dir / "experiments.jsonl",
    )
```

**Why:** Eliminates duplicate fixture code, ensures security compliance, automatic cleanup.

### Module-Level vs In-Fixture Imports

**Pattern:** Place imports at module level, not inside fixtures:

```python
# CORRECT
import shutil  # At module level

def test_example(data_temp_dir):
    shutil.rmtree(data_temp_dir)  # Use directly

# WRONG
def test_example(data_temp_dir):
    import shutil  # Inside function - performance hit
    shutil.rmtree(data_temp_dir)
```

**Why:** Performance, consistency, better IDE support.

---

## Usage Guidelines

**For AI Agents:**

1. **Read before implementing**: Always review this file before writing code
2. **Follow all rules**: Every rule here prevents common mistakes
3. **When in doubt**: Choose the more restrictive, safer option
4. **Update as needed**: Add new patterns discovered during implementation
5. **Use examples**: Copy patterns from the code examples provided
6. **Test thoroughly**: Follow testing rules to ensure quality
7. **Maintain compatibility**: Use compat.py pattern when refactoring

**For Humans:**

1. **Keep it lean**: Remove rules that become obvious over time
2. **Update quarterly**: Review when technology stack changes
3. **Add discoveries**: Document new patterns as they're found
4. **Remove outdated**: Delete rules for deprecated patterns
5. **Validate rules**: Ensure all rules are still relevant and accurate

**Maintenance Schedule:**
- Weekly: Add new patterns discovered during development
- Monthly: Review and optimize for LLM context efficiency  
- Quarterly: Full review for outdated or redundant rules
- Annually: Technology stack version updates

---

_Last Updated: 2026-03-12_
_Status: Complete - 22 patterns documented, ResearchAgent + Compound stabilized_
_Sections: 10 (all complete)_
_Research Module: 37 tests, 100% pass rate_
_Compound Module: 941 tests, 100% pass rate_
_Total Tests: 978 passing, 0 failures_
_Optimized for: LLM context efficiency + token-minimal execution_
