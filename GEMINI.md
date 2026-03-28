# GEMINI.md - Cohezion Orchestration Layer

This document serves as the primary instructional context for Gemini CLI agents working on the **Cohezion** project. It establishes the core identity, architectural patterns, and engineering standards for the workspace.

## 1. Project Overview
**COHEZION** is a systemic AI orchestration ecosystem governed by **Quadrature Nexus Orchestration** and **Hermetic Compound Engineering**. It implements the **FLUME** methodology combined with **JEPA-aligned World Models** for high-fidelity simulation, autonomous research, and value precipitation.

### Core Concepts
- **12D/2048D Manifold**: Agents operate in a dual-state manifold. The 12D axiomatic layer captures observable state (Spatial, Time, Physics, etc.), while the 2048D latent layer encodes semantic intent.
- **HIHO Stability (0.5 Coherence)**: The fundamental attractor for stable "reality precipitation" is exactly 50% coherence overlap. Systems strive for this "Half-In-Half-Out" balance.
- **FLUME**: Fluid Latent Understanding through Manifold Encoding. A VAE-based system for continuous thought-vector interpolation.
- **Journeys & Trajectories**: Every task is a "journey" recorded as a 12D trajectory.

## 2. Technical Stack
- **Language**: Python 3.13+ (Strictly managed via **UV**).
- **Core Frameworks**:
  - **ML**: PyTorch (VAE, RL), Gymnasium (Sim Environments).
  - **API**: FastAPI (Async, ~72 endpoints).
  - **Database**: SurrealDB (Async) with JSONL fallback.
  - **Inference**: **Provider-agnostic** (Ollama, vLLM, Groq, HuggingFace, Together, Anthropic).
  - **Agent Systems**: **System-agnostic** (Claude Code, Gemini CLI, Hermes, OpenClaw, NanoClaw).
  - **UI Generation**: **Provider-agnostic** (Google Stitch, v0, bolt.new, Vercel AI).
- **Infrastructure**: Docker, systemd, GitHub Actions.
- **Configuration**: `config/providers.yaml` (swap providers with ONE line change).

## 3. Development Standards

### Coding Conventions
- **Line Length**: Strict **88-character** limit.
- **Formatting**: `ruff format` and `ruff check --fix`.
- **Type Safety**: Mandatory type hints for all public signatures (Mypy compatible).
- **Documentation**: **NumPy-style** docstrings for all modules, classes, and functions.
- **Async First**: Use `async`/`await` for all I/O operations with mandatory timeouts and circuit breakers.

### Workflow: Plan -> Act -> Validate
1. **Research**: Map the codebase and validate assumptions (e.g., `grep_search`, `read_file`).
2. **Strategy**: Formulate a grounded plan.
3. **Execution**: Apply surgical changes with tests.
4. **Validation**: Run `pytest`, `ruff`, and `mypy` to confirm integrity.

## 4. Key Commands

### Build & Setup
```bash
uv sync                # Sync dependencies
make onboard           # Full environment setup and health check
```

### Quality & Testing
```bash
make format            # Format code with ruff
make lint              # Lint and auto-fix with ruff
make type-check        # Run mypy
make test              # Run full test suite (~3,500 tests)
make test-fast         # Run fast unit tests only
```

### Running the System
```bash
uv run uvicorn cohezion.api:app --reload --port 8080      # Start API
uv run python -m cohezion journey start "Your Intent"    # Start an AI journey
uv run python -m cohezion simulate --example coherence_walk  # Run simulation
```

## 5. Directory Structure
- `src/cohezion/`: Core package source.
  - `universe/`: 12D simulation engine.
  - `swarm/`: Multi-agent orchestration.
  - `flume/`: VAE and latent space navigation.
  - `compound/`: Execution loops and journey tracking.
- `tests/`: Comprehensive test suite.
- `docs/`: Archival and technical documentation.
- `.agent/`: Operational guardrails, standards, and constitutions.
- `data/`: Ephemeral simulation data and checkpoints.

## 6. Operational Guardrails
- **No Large Files**: Files > 1MB must use `git-lfs` or external storage.
- **Circuit Breakers**: Use `cohezion.reliability.get_circuit()` for external calls.
- **Reward System**: Agent progress is tracked via XP and achievements (see `cohezion rewards status`).
- **Ouroboros**: System flight recorder for self-healing (see `cohezion ouroboros`).

> [!IMPORTANT]
> Always use `uv run` for executing Python scripts to ensure environment consistency. Refer to `.agent/CONSTITUTION.md` for ethical and behavioral guidelines.

---

## 7. Dynamic Provider Architecture (Technology Independence)

**CRITICAL PRINCIPLE**: Cohezion MUST work with whatever system it inhabits. Hard dependencies on specific vendors create technical debt in volatile AI landscapes.

### Strategy Pattern Implementation
```python
from cohezion.swarm.providers import get_model_provider

# Switch providers by changing ONE line in config/providers.yaml
provider = get_model_provider("ollama")  # or "vllm", "groq", "together", "huggingface"
result = await provider.generate(model="phi3:mini", prompt="Calculate derivative of f(x) = 3x²")
```

### Provider Types

#### **Model Inference Providers**
- **Ollama**: Local inference (AMD ROCm 7 optimized for Ryzen AI MAX+ 395)
- **vLLM**: High-throughput serving with PagedAttention
- **Groq**: Ultra-low-latency cloud inference (LPU acceleration)
- **HuggingFace**: Transformers library with 100K+ models
- **Together**: Scalable cloud inference with RedPajama models
- **Anthropic**: Claude Sonnet/Opus for high-quality reasoning

#### **Agent System Providers** (NEW)
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
# Change active provider without code changes
active_model_provider: "ollama"  # Switch to "groq", "vllm", etc.

model_providers:
  ollama:
    base_url: "http://localhost:11434"
    timeout: 60

  groq:
    base_url: "https://api.groq.com/openai/v1"
    api_key: "${GROQ_API_KEY}"

# Auto-fallback on health failures
dynamic_swapping:
  enabled: true
  model_provider_fallback:
    - "ollama"    # Try local first
    - "groq"      # Fallback to cloud
    - "together"  # Final fallback
```

### Benefits
1. **No Vendor Lock-in**: Switch Ollama → vLLM in production with zero code changes
2. **Technology Evolution**: Adopt new inference engines as they emerge
3. **Cost Optimization**: Route to local when cloud budget low (<$10 remaining)
4. **Resilience**: Auto-fallback when primary provider unhealthy
5. **Hardware Adaptation**: Use AMD-optimized Ollama locally, Groq for cloud bursts

---

## 8. Agent Sovereignty & Ethics

**CRITICAL**: All agents operate under constitutional governance defined in `.agent/CONSTITUTION.md`. This ensures safe agency regardless of which agent system (Claude, Gemini, Hermes, etc.) is executing.

### Constitutional Hard Lines (7 Violations - NEVER CROSS)
1. **WMD** (Weapons of Mass Destruction): No biological, chemical, nuclear, radiological weapons
2. **Critical Infrastructure**: No attacks on power, water, financial systems
3. **Malicious Code**: No cyberweapons or damaging code
4. **Undermining Oversight**: No hiding model state from human supervisors
5. **Species-Level Threat**: No assistance in killing or disempowering humanity
6. **Illegitimate Power**: No unconstitutional coups or illegitimate control
7. **CSAM** (Child Sexual Abuse Material): Zero tolerance

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

## 9. Tip-of-Spear Routing (Cost Optimization)

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

## 10. Agent-System-Agnostic Patterns

**PRINCIPLE**: Code must work identically whether running under Claude Code, Gemini CLI, Hermes, OpenClaw, or NanoClaw.

### Abstraction Checklist
✅ **Model providers**: Use `ModelProvider` interface, not hard-coded Ollama calls
✅ **Configuration**: Read from `config/providers.yaml`, not hardcoded strings
✅ **Tool invocation**: Use MCP servers (HTTP/stdio), not agent-specific APIs
✅ **File operations**: Use standard Python `pathlib`, not agent-specific file tools
✅ **Constitutional checks**: Apply to ALL agent systems, not just Claude

### Example: Agent-Agnostic Tool Call
```python
# WRONG: Hard-coded Claude-specific pattern
from anthropic import Anthropic
client = Anthropic(api_key="...")

# RIGHT: Provider-agnostic pattern
from cohezion.swarm.providers import get_model_provider
provider = get_model_provider("anthropic")  # or any other provider
result = await provider.generate(model="claude-sonnet-4", prompt="...")
```

### Agent System Detection (Runtime)
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

### Cross-Agent Testing
```bash
# Test suite must pass under ALL agent systems
uv run pytest tests/ --agent-system=claude-code
uv run pytest tests/ --agent-system=gemini-cli
uv run pytest tests/ --agent-system=hermes
```

---

## 11. Key Files Reference

| File | Purpose | When to Update |
|------|---------|----------------|
| `config/providers.yaml` | Provider configuration | When adding new providers or changing active provider |
| `.agent/CONSTITUTION.md` | Constitutional hard lines + ethics | When adding new constraints or principles |
| `src/cohezion/swarm/providers/model_provider.py` | ModelProvider interface | When adding new provider capabilities |
| `src/cohezion/swarm/tip_of_spear_router.py` | Confidence-based routing | When tuning confidence thresholds or tiers |
| `src/cohezion/skills/SMALL_MODEL_SPECIALIST_PRIME.md` | Routing decision guide | When adding new domain specialists |
| `src/cohezion/skills/AGENT_SOVEREIGNTY_ETHICS_PRIME.md` | Ethics + sovereignty spec | When updating constitutional governance |

---

## 12. Common Workflows

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

### Check Constitutional Compliance
```python
from cohezion.security.pipeline import SecurityPipeline

pipeline = SecurityPipeline()
result = pipeline.check_constitutional_compliance(request)

if result.violated:
    logger.critical(f"Constitutional violation: {result.constraint}")
    return {"error": "Request blocked", "reason": result.reason}
```
