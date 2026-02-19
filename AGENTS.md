# AGENTS.md - Agentic Coding Guidelines for Cohezion

## 1. Build, Lint, and Test Commands

### Core Commands
```bash
make format          # ruff format .
make lint            # ruff check --fix .
make lint-check      # ruff check . && ruff format --check .
make type-check      # mypy --ignore-missing-imports src/cohezion/
make test            # uv run pytest tests/
make test-fast       # uv run pytest -m fast --tb=short tests/
make all             # format && lint && type-check && test
```

### Running Single Tests
```bash
uv run pytest tests/test_myfile.py::test_my_function -v
uv run pytest tests/test_myfile.py::TestMyClass -v
uv run pytest tests/ -m fast -v
```

## 2. Code Style Guidelines

- **Python**: 3.13+ required
- **Package manager**: Always use `uv` (never bare `python`/`pip`)
- **Formatter**: ruff (line length 88)
- **Type hints**: Mandatory; use `str | None` not `Optional[str]`

### Imports
- Use isort with `known-first-party = cohezion`
- Sort: stdlib → third-party → first-party
- Two blank lines between groups

### Naming
- Functions/variables: snake_case
- Classes: PascalCase
- Constants: SCREAMING_SNAKE_CASE
- Files: snake_case.py

### Docstrings
- NumPy-style: Start capital, end with period
- Document "why" not "what" - state assumptions and intent

### Async Code
- All I/O must be `async/await` with timeouts
- Example: `async with httpx.AsyncClient(timeout=30.0) as client:`

### Error Handling
- Use specific exception classes (not bare `Exception`)
- Include circuit breakers for external services

### Validation
- Use Pydantic at input/output boundaries

### Comments
- NO comments unless explicitly requested

### Testing
- Tests in `tests/` directory, naming `test_*.py`
- Markers: `@pytest.mark.fast`, `@pytest.mark.integration`, `@pytest.mark.mcp`
- **CRITICAL**: Mock at source, not after import:
  ```python
  # CORRECT
  @patch("cohezion.swarm.compound_client.get_compound_client")
  # WRONG
  @patch("cohezion.api.compound_client")
  ```

## 3. Git Workflow

### Worktree Pattern (MANDATORY for Claude sessions)
```bash
SESSION_ID=57
PHASE="feature-name"
git worktree add ~/dev/cohezion-session-${SESSION_ID} -b session-${SESSION_ID}-${PHASE}
```

### Branch Naming
- `session-*` - Claude session branches
- `feature/*`, `fix/*`, `refactor/*`, `docs/*`

### Commit Messages
- Conventional: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
- No emoji, subject under 72 chars
- AI commits: include `Co-Authored-By: Claude <noreply@anthropic.com>`

## 4. Project Structure

```
src/cohezion/
├── api/              # FastAPI endpoints
├── compound/         # Compound executor, skill refinement
├── swarm/            # Multi-agent orchestration
├── cache/            # Semantic cache (L1/L2/L3)
├── skills/           # PRIME skill definitions
├── persistence/      # SurrealDB, session recovery
├── core/             # MCP client, context engineering
├── flume/            # FLUME VAE (256D latent space)
tests/
├── compound/
├── swarm/
├── core/
└── conftest.py       # Shared fixtures + singleton resets
```

## 5. Key Patterns

### Singleton Reset (Critical for Tests)
```python
def _reset_all_singletons():
    from cohezion.api import reset_flume_vae
    from cohezion.swarm import reset_pool_manager
    reset_flume_vae()
    reset_pool_manager()
```

### Journey Tracking
```python
from cohezion.compound.journey_tracker import JourneyTracker
tracker = JourneyTracker()
state = tracker.record_state(
    agent_id="agent-1",
    phase="execution",
    position={"x": 0.5, ...},  # 12D coordinates
    coherence=0.87,
    context=request_state
)
```

### Request Alignment Analysis
```python
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer
analyzer = RequestAlignmentAnalyzer()
alignment = analyzer.analyze(request, available_skills, agent_context)
if alignment.coherence < 0.5:
    logger.warning(f"Low coherence: {alignment.issues}")
```

## 6. Vault Integration

```python
from cohezion.core.mcp_client import get_mcp_client
client = get_mcp_client()
client.vault_log_decision(
    project="cohezion",
    title="Short title",
    context="What led to this decision",
    decision="What was decided",
    rationale="Why this option was chosen"
)
```

## 7. Skills

Specialized skills can be loaded for domain-specific tasks. Available skills are in `.claude/skills/`.

To load a skill, use the Skill tool with the skill name. The skill injects detailed instructions into the conversation context.

### Available Skills

| Skill | Description | When to Use |
|-------|-------------|-------------|
| `systemd-crash-loop-prevention` | Harden systemd services to prevent infinite crash loops | Service crash-looping, creating new systemd services, seeing "Start request repeated too quickly" errors |

### Loading a Skill

```python
# In Claude Code / opencode:
# Use the Skill tool with name="systemd-crash-loop-prevention"
```

## 8. Hardware Constraints (Strix Halo)

- **CPU**: AMD Ryzen AI MAX+ 395 (16C/32T)
- **GPU**: Radeon 8060S (iGPU, unified memory)
- **RAM**: 128 GiB LPDDR5X
- **Local Models**: Ollama (max 4 concurrent)
- **Never assume CUDA/RTX availability**
