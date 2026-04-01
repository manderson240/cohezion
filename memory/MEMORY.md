# Cohezion Compiled Memory

**Auto-compiled from `~/vaults/cohezion-vault/` - Query vault for full context**

**Last Updated**: 2026-04-01 (Session 86)

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

## Active Context (Session 86, 2026-04-01)

**Branch**: `main` (16 commits ahead of origin)
**Recent Sessions (79-85)**:
- S79: 32 commits merged to main (Genesis TDD, A2UI, AG-UI, Observer Patch, Concierge, Data Mesh)
- S80: GeminiProvider, CostAwareRouter Gemini tiers, A2A agent cards, knowledge capture E2E, FLUME retrained
- S81: Internal sweep (41 disconnected modules found), LatentMAS/DeltaKV/SALS research
- S83-84: Autonomous overnight operation (52 cycles), OI-MAS routing, TurboQuant, LatentMAS channel, orphan wiring
- S85: PPO training breakthrough — small actions cooperate with physics (HIHO thesis validated!)
- TDD: RoutingOrchestrator, CapabilityMatrix gap detection, ManifoldEnv curriculum reward
- Research paper draft: Physics-Grounded Training Universes
**Test Suite**: 6,000 collected
**Source Lines**: 172,644
**Ruff**: 33 fixable (down from 800+)
**Coverage**: ~23%
**Next Steps**:
1. Wire validation/constitutional → CompoundExecutor runtime enforcement
2. Consolidate healing/ + resilience/ → single AutonomicManager
3. Wire MCP HTTP→stdio for top 4 servers
4. LatentMAS integration — FLUME vectors as agent-to-agent communication
5. Register ManifoldEnv/SwarmEnv with Gymnasium
6. Delete confirmed dead code (evaluation/, pipelines/, storage/)
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
