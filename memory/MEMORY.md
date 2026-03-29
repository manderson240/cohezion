# Cohezion Compiled Memory

**Auto-compiled from `~/vaults/cohezion-vault/` - Query vault for full context**

**Last Updated**: 2026-03-28 (Session 77)

---

## Recent Decisions (Last 7 Days)

### 2026-02-20: Self-Healing Protocol Validation
- **Context**: Ruff linting errors at 1,058, missing `__init__.py` files across 18 directories
- **Decision**: Execute `/heal` command to trigger autonomic diagnostics and auto-fix
- **Outcome**: Reduced errors to 1,003 (-5.2%), created missing package files, validated graceful degradation
- **Rationale**: Systematic cleanup via orchestrated tooling > manual fixes. Compound engineering principle.

### 2026-02-20: README Metrics Correction
- **Context**: README.md claimed 134 PRIME skills, actual count 74; claimed 351 Python files, actual 401
- **Decision**: Update README with verified metrics from live codebase scan
- **Outcome**: Adversarial verification restored - all claims now match reality
- **Rationale**: Honesty is non-negotiable (Constitution §4). False metrics undermine trust.

### 2026-02-10: API God Object Decoupling (Learning 119)
- **Context**: Monolithic `api/__init__.py` contained VAE/RL training logic
- **Decision**: Extract to dedicated services (flume.py, rl.py, skills.py)
- **Outcome**: Reduced coupling, enabled independent scaling, safer unit testing
- **Rationale**: God objects are architectural contagion - violate single responsibility

### 2026-02-10: Soft Schema Enforcement (Learning 120)
- **Context**: LLM JSON outputs caused KeyError crashes in PatternScout
- **Decision**: Implement `.get()` with intelligent defaults before Pydantic validation
- **Outcome**: Prevented catastrophic swarm failures during semantic scouting
- **Rationale**: First line of defense for non-deterministic outputs - fail gracefully

---

## Most-Used Patterns (Top 10)

1. **Mock at Source Module** (Learning 110) - Patch `cohezion.swarm.compound_client.get_compound_client`, not import sites
2. **Singleton Reset in conftest.py** - FLUME VAE + RL policy + logger handlers (prevents test pollution)
3. **Batching Inside Rust** (Learning 28) - 29x speedup over naive 1:1 FFI calls
4. **3-Beat Actuation** (Learning 30) - Require 3 consecutive low-coherence beats before triggering repair
5. **HIHO Stability** (0.5 coherence) - Constitutional requirement, validated over 25M cycles
6. **Layered Defense** (Learning 96) - Schema validation at: pre-commit, PostToolUse, unit tests, scaffolding
7. **Graceful Fallback** - SurrealDB → InMemoryStore under connection failure
8. **Worktree Isolation** - Every Claude session creates feature branch to prevent conflicts
9. **Pre-flight Checks** - 9-step pipeline validates Ollama/SurrealDB before execution
10. **Deterministic Responsibility** - Idempotency keys for all external calls

---

## Critical Invariants (Never Violate)

| Invariant | Enforcement | Violation Recovery |
|-----------|-------------|-------------------|
| HIHO coherence = 0.5 | Constitution §3 | Thermal trend predictor triggers repair |
| Honest metrics | README vs codebase | Adversarial verification + correction |
| Test isolation | conftest.py singleton reset | Run pytest in fresh interpreter |
| Package integrity | Every src/ dir has `__init__.py` | `/heal` command auto-creates |
| Idempotent actions | All external calls use keys | Checkpoint rollback |
| No sudo in automation | VRAM via sysfs, not privileged | Direct AMD /sys telemetry |
| Vault-first knowledge | Query before writing | `vault_find_relevant_context()` |
| Git worktree per session | Branch isolation | `git worktree cleanup` |

---

## Active Context (Session 77, 2026-03-28)

**Current Work**: Full project health fix — MCP config, hooks, worktree cleanup
**Branch**: `challenge/nvidia-nemotron-reasoning`
**Recent**:
- Fixed BMAD MCP server config (streamable-http → stdio)
- Fixed SurrealDB health check port (8000 → 8001)
- Fixed branch-safety-warning hook false positive (allows writes outside repo)
- Removed 3 stale empty dirs (flux, vibe, graph)
- Fixed ruff target-version (py311 → py313)
- Preserved 3 worktree WIP commits + 11 stashes → archive branches
- Killed stale BMAD zombie process
**Test Suite**: 5,001 collected (1 pre-existing failure in A2A endpoints)
**Ruff**: ~5 auto-fixable violations (from py313 target change)
**Next Steps**:
1. Phase 2: Decompose monoliths (api/__init__.py, executor.py)
2. Phase 3: Coverage 21%→40%, security lint audit
3. Phase 4: CI hardening (coverage floor, type check gate)

**Velocity**: Moderate (config fixes, cleanup, retrospective)
---

## Quick Reference Commands

```bash
# Full test suite
uv run pytest tests/ -q

# Self-healing protocol
uv run python3 src/cohezion/healing/immune_system.py

# Linting + formatting
uv run ruff check src/cohezion/ --fix
uv run ruff format src/cohezion/

# Verify metrics
uv run pytest tests/ --collect-only -q | tail -1  # Test count
jq '. | length' src/cohezion/skills/skill_registry.json  # Skill count

# SurrealDB connection test
uv run python -c "from cohezion.core.persistence.surreal_client import SurrealClient; import asyncio; asyncio.run(SurrealClient().connect())"
```

---

## Vault Query Examples

```python
# Find relevant context before writing code
from cohezion.skills.cohezion_mcp import vault_find_relevant_context
context = vault_find_relevant_context(query="test isolation singleton reset")

# Log new decisions
from cohezion.skills.cohezion_mcp import vault_log_decision
vault_log_decision(
    project="cohezion",
    title="SurrealDB Auth Fallback",
    context="Persistent InvalidAuth error during /heal",
    decision="Graceful fallback to InMemoryStore",
    rationale="System stability > strict persistence"
)
```

---

**Token Budget**: This file is ~125 lines (target <200). For full history, query `~/vaults/cohezion-vault/`.
