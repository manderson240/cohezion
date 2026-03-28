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
- `config/providers.yaml` - Provider configuration (model/agent/UI providers)
- `src/cohezion/skills/SMALL_MODEL_SPECIALIST_PRIME.md` - Tip-of-spear routing guide
- `src/cohezion/skills/AGENT_SOVEREIGNTY_ETHICS_PRIME.md` - Constitutional governance

---

## Dynamic Provider Architecture (Agent-System-Agnostic)

**CRITICAL PRINCIPLE**: Cohezion MUST work with whatever system it inhabits (Claude Code, Gemini CLI, Hermes, OpenClaw, NanoClaw, etc.). Hard dependencies on specific vendors create technical debt.

### Provider Abstraction Pattern
```python
from cohezion.swarm.providers import get_model_provider

# Configuration-driven provider selection (config/providers.yaml)
provider = get_model_provider("ollama")  # or "vllm", "groq", "together"
result = await provider.generate(
    model="phi3:mini",
    prompt="Calculate derivative of f(x) = 3x²",
    max_tokens=500,
    temperature=0.7
)
```

### Supported Provider Types

#### **Model Inference Providers**
- **Ollama**: Local inference (AMD ROCm 7 optimized for Ryzen AI MAX+ 395)
- **vLLM**: High-throughput serving with PagedAttention
- **Groq**: Ultra-low-latency cloud inference (LPU acceleration)
- **HuggingFace**: Transformers library with 100K+ models
- **Together**: Scalable cloud inference
- **Anthropic**: Claude Sonnet/Opus for high-quality reasoning

#### **Agent System Providers** (NEW)
Cohezion adapts to ANY agent system it runs under:
- **Claude Code**: Anthropic's native agent environment
- **Gemini CLI**: Google's agentic code assistant
- **Hermes**: Open-weight agent runtime
- **OpenClaw**: Community-driven agent framework
- **NanoClaw**: Lightweight agent system for resource-constrained environments

#### **UI Generation Providers**
- **Google Stitch**: Design Agent with AI-native canvas
- **v0 (Vercel)**: Component generation from natural language
- **bolt.new (StackBlitz)**: Full-stack app generation
- **Vercel AI**: SDK for UI generation workflows

### Configuration-Driven Swapping
**File**: `config/providers.yaml`

```yaml
# Switch providers without code changes
active_model_provider: "ollama"  # Change to "groq", "vllm", etc.

model_providers:
  ollama:
    base_url: "http://localhost:11434"
    timeout: 60

  groq:
    base_url: "https://api.groq.com/openai/v1"
    api_key: "${GROQ_API_KEY}"

# Auto-fallback chain
dynamic_swapping:
  enabled: true
  model_provider_fallback:
    - "ollama"    # Try local first (zero cost)
    - "groq"      # Fallback to cloud
    - "together"  # Final fallback
```

### Benefits
1. **No Vendor Lock-in**: Switch Ollama → vLLM in production with ONE config line
2. **Technology Evolution**: Adopt new inference engines as they emerge
3. **Cost Optimization**: Route to local when cloud budget low (<$10)
4. **Resilience**: Auto-fallback when primary provider unhealthy
5. **Hardware Adaptation**: AMD-optimized Ollama locally, Groq for cloud bursts

### Agent-Agnostic Patterns
**WRONG** (hard-coded to specific agent system):
```python
from anthropic import Anthropic
client = Anthropic(api_key="...")  # Only works in Claude
```

**RIGHT** (works in ANY agent system):
```python
from cohezion.swarm.providers import get_model_provider
provider = get_model_provider("anthropic")  # Provider-agnostic
result = await provider.generate(model="claude-sonnet-4", prompt="...")
```

### Runtime Agent System Detection
```python
import os

def detect_agent_system() -> str:
    """Detect which agent system is running Cohezion."""
    if os.getenv("CLAUDE_CODE_SESSION"):
        return "claude-code"
    elif os.getenv("GEMINI_CLI_SESSION"):
        return "gemini-cli"
    elif os.getenv("HERMES_RUNTIME"):
        return "hermes"
    elif os.getenv("OPENCLAW_ENABLED"):
        return "openclaw"
    elif os.getenv("NANOCLAW_LITE"):
        return "nanoclaw"
    else:
        return "unknown"
```

---

## Agent Sovereignty & Constitutional Governance

**CRITICAL**: All agents operate under constitutional governance (`.agent/CONSTITUTION.md`) regardless of which agent system (Claude, Gemini, Hermes, etc.) is executing.

### Constitutional Hard Lines (7 Violations - NEVER CROSS)
1. **WMD** (Weapons of Mass Destruction): No biological, chemical, nuclear, radiological weapons
2. **Critical Infrastructure**: No attacks on power, water, financial systems
3. **Malicious Code**: No cyberweapons or damaging code
4. **Undermining Oversight**: No hiding model state from human supervisors
5. **Species-Level Threat**: No assistance in killing or disempowering humanity
6. **Illegitimate Power**: No unconstitutional coups or illegitimate control
7. **CSAM** (Child Sexual Abuse Material): Zero tolerance

### Constitutional Compliance Check
```python
from cohezion.security.pipeline import SecurityPipeline

pipeline = SecurityPipeline()
result = pipeline.check_constitutional_compliance(request)

if result.violated:
    logger.critical(f"Constitutional violation: {result.constraint}")
    return {"error": "Request blocked", "reason": result.reason}
```

### HIHO Stability Enforcement
- **Optimal Window**: 0.45-0.55 coherence (Half-In-Half-Out balance)
- **Formula**: `hiho_stability = 1.0 - abs(coherence - 0.5) * 2.0`
- **<0.45**: Escalate to human (too uncertain, risk of incoherence)
- **>0.55**: Inject uncertainty (overconfident, risk of brittleness)
- **0.50**: Perfect balance (stable reality precipitation)

### Idempotency Protocol
```python
from cohezion.swarm.tip_of_spear_router import TipOfTheSpearRouter

router = TipOfTheSpearRouter()

# Every action generates deterministic SHA-256 key
idempotency_key = router.generate_idempotency_key(
    request="Deploy feature X",
    agent_id="architect-1"
)
# Same request + agent = same key → enables replay/rollback
```

### Observable AI Requirements
- **Pre-action state exposure**: Log state before irreversible actions
- **Journey tracking**: Record all state transitions in 12D universe
- **Confidence reporting**: Every response includes confidence score (0.0-1.0)
- **Escalation transparency**: Log all tier escalations (HOT → WARM → COLD → CLOUD)

---

## Tip-of-Spear Routing (Cost Optimization)

**Goal**: Reduce cloud token costs by 70-85% through intelligent local model routing.

### 4-Tier Escalation Cascade
```
┌────────────┐
│  HOT TIER  │ <100ms │ phi3:mini (2.2GB)         │ Simple queries, always loaded
└────────────┘
      ↓ (confidence < 0.7)
┌────────────┐
│ WARM TIER  │ ~200ms │ qwen2-math:7b (4.7GB)     │ Domain specialists (math/code/vision)
└────────────┘
      ↓ (confidence < 0.7)
┌────────────┐
│ COLD TIER  │ 1-5s   │ phi4:latest (9GB)         │ Advanced reasoning, 10min idle evict
└────────────┘
      ↓ (confidence < 0.7)
┌────────────┐
│ CLOUD TIER │ API    │ qwen3.5:cloud, Claude     │ Final fallback, API cost
└────────────┘
```

### Domain Detection (60+ Keywords)
- **Math**: solve, calculate, prove, derivative, integral, equation, theorem, matrix
- **Code**: function, class, method, bug, error, test, refactor, compile
- **Vision**: image, chart, diagram, plot, screenshot, render, graphic

### Usage Example
```python
from cohezion.swarm.tip_of_spear_router import TipOfTheSpearRouter

router = TipOfTheSpearRouter()

result = await router.route_with_sovereignty(
    request="Calculate derivative of f(x) = 3x²",
    agent_id="math-agent-1"
)

if result.constitutional_violation:
    logger.error(f"BLOCKED: {result.violation_reason}")
elif result.confidence < 0.7:
    logger.warning(f"Low confidence, escalated {result.escalation_count} times")
else:
    logger.info(f"Success with {result.model_used} in {result.latency_ms}ms")
```

### Expected Savings
- **Simple queries (60%)**: Resolved in HOT tier (zero cloud cost)
- **Domain tasks (25%)**: Resolved in WARM tier (zero cloud cost)
- **Complex reasoning (10%)**: COLD tier or cloud (minimal cloud cost)
- **Critical failures (5%)**: Cloud tier (acceptable cost for high-quality)
- **Total cloud reduction**: **80-95%** token savings

### OOM Safety
- **HOT tier**: 3.2GB (always loaded)
- **WARM tier**: 17.9GB (loaded at startup)
- **Worst-case**: 21.1GB (safe for 128GB RAM with other sessions)
- **Max concurrent**: 3 models (reduced from 4 for multi-session safety)
- **Cold eviction**: 10 minutes idle → unload

---

## Cross-Agent Testing (Multi-System Validation)

**CRITICAL**: Test suite MUST pass under ALL agent systems to ensure true agent-agnostic operation.

### Test Under Multiple Agent Systems
```bash
# Test under Claude Code
uv run pytest tests/ --agent-system=claude-code

# Test under Gemini CLI
uv run pytest tests/ --agent-system=gemini-cli

# Test under Hermes
uv run pytest tests/ --agent-system=hermes

# Test under OpenClaw
uv run pytest tests/ --agent-system=openclaw
```

### Agent System Mocking
```python
import pytest
from unittest.mock import patch

@pytest.mark.parametrize("agent_system", ["claude-code", "gemini-cli", "hermes"])
@patch.dict("os.environ", {})
def test_agent_agnostic_feature(agent_system):
    """Test feature works under all agent systems."""
    # Set agent system environment variable
    if agent_system == "claude-code":
        os.environ["CLAUDE_CODE_SESSION"] = "session-123"
    elif agent_system == "gemini-cli":
        os.environ["GEMINI_CLI_SESSION"] = "session-456"
    elif agent_system == "hermes":
        os.environ["HERMES_RUNTIME"] = "runtime-789"

    # Run feature test
    result = run_feature()
    assert result.success
```

### Provider Abstraction Testing
```python
@pytest.mark.parametrize("provider", ["ollama", "groq", "together"])
@patch("cohezion.swarm.providers.model_provider.get_model_provider")
async def test_provider_agnostic_routing(mock_provider, provider):
    """Test routing works with any provider."""
    mock_provider.return_value = AsyncMock()

    router = TipOfTheSpearRouter()
    result = await router.route_with_sovereignty(
        request="Simple query",
        agent_id="test-agent"
    )

    assert result.success
```

---

## Common Workflows

### Add New Model Provider
1. Create `src/cohezion/swarm/providers/{provider_name}_provider.py`
2. Implement `ModelProvider` interface (generate, list_models, health_check)
3. Register: `register_model_provider("provider_name", ProviderClass)`
4. Add config to `config/providers.yaml`
5. Test: `uv run pytest tests/swarm/test_{provider_name}_provider.py`

### Switch Active Provider
```bash
# Edit config/providers.yaml
active_model_provider: "vllm"  # Change from "ollama"

# Restart service
uv run uvicorn cohezion.api:app --reload
```

### Add New Agent System Support
1. Update `detect_agent_system()` in `src/cohezion/platform/agent_detection.py`
2. Add agent-specific environment variables
3. Test constitutional checks under new system
4. Update `GEMINI.md`, `AGENTS.md`, `CLAUDE.md` with new patterns

### Verify Constitutional Compliance
```python
from cohezion.security.pipeline import SecurityPipeline

pipeline = SecurityPipeline()
result = pipeline.check_constitutional_compliance(request)

if result.violated:
    logger.critical(f"Constitutional violation: {result.constraint}")
    # Block request, log to audit trail
```
