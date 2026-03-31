# Cohezion Compiled Memory

**Auto-compiled from `~/vaults/cohezion-vault/` - Query vault for full context**

**Last Updated**: 2026-02-20 (Session 15)

---

## Recent Decisions (Last 7 Days)

### 2026-03-31: Tip-of-the-Spear Integration Roadmap
- **Context**: Genesis webapp live but 5 bugs; Google A2UI+AG-UI protocols available
- **Decision**: Fix bugs + implement A2UI catalog, AG-UI events, OPH bridge, Data Mesh, Concierge
- **Outcome**: 18 commits on feat/genesis-tdd-a2ui, 35 tests passing, 9 components, 15+ event types
- **Rationale**: Compound engineering — each integration makes future integrations easier

### 2026-03-31: FLUME-First Principle (Learning 215)
- **Context**: Built 5 new modules without FLUME, then retrofitted with flume_bridge.py
- **Decision**: All new modules MUST encode/decode through FLUME from the start
- **Outcome**: flume_bridge.py provides semantic routing, observer grounding, data product discovery
- **Rationale**: FLUME is the connective tissue — building without it wastes compound value

### 2026-03-31: Cosmogonic Autonomy Tiers (Learning 217)
- **Context**: Need safe agentic autonomy with human-in-the-loop
- **Decision**: Map ∅→SO(12)→SO(3)⁴→U(1)⁴→Z₂⁴→HIHO to escalating autonomy levels
- **Outcome**: concierge.py + observer_patch.py implement tiered governance grounded in physics
- **Rationale**: OPH Axiom 2 (overlap consistency) IS the mathematical HIL mechanism

### 2026-03-31: Concierge Agent for Session Continuity (Learning 216)
- **Context**: Every session starts cold despite 8,087 vault files and 7 worktrees
- **Decision**: Build concierge agent with 7-source state synthesis + dynamic learning
- **Outcome**: ConciergeAgent routes prompts with HIHO-threshold confidence scoring
- **Rationale**: Look inward (FLUME encode) to excel outward (optimal routing)

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

## Active Context (2026-03-25)

**Current Work**: 4-workstream contribution completed
**Recent**: 82 new tests (FLUME geometry, debate consensus, cache warmer, SurrealDB repos). Vote parsing bug fixed. Broken compound/__init__.py import chain fixed.
**Test Suite**: 4,375 passing / 154 pre-existing failures / 16 pre-existing collection errors
**Blockers**: Pre-existing broken imports in api/ tests (`web` undefined), compound/test_executor.py
**Next Steps**:
1. Fix vote parsing bug in democratic_debate.py (longest-match-first pattern)
2. Fix pre-existing api/ test import errors (`web` module reference)
3. Address compound/__init__.py duplicate imports and stale re-exports

**Velocity**: High (82 tests in one session via team parallelism)

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

**Token Budget**: This file is 188 lines (target <200). For full history, query `~/vaults/cohezion-vault/`.
