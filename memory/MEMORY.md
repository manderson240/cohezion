# Cohezion Compiled Memory

**Auto-compiled from `~/vaults/cohezion-vault/` - Query vault for full context**

**Last Updated**: 2026-04-08 (Session 91 retrospective)

---

## Recent Decisions (Last 7 Days)

### 2026-04-07: MCP stdio Transport Rules (L273-L275)
- **Context**: gemini mcp servers showing "Disconnected" status after plugin/config changes
- **Decision**: Three hard rules for all stdio MCP servers: (1) YAML frontmatter mandatory in AGENTS.md (`name`+`description`), (2) config lookups MUST be lazy (`get_config()` not globals — Bitwarden vault checks at import caused handshake timeout), (3) servers MUST be silent on stdout during init (logger.info + `uv run` update checks corrupt the protocol stream — use `.venv/bin/python` or `uv -q run`)
- **Outcome**: Restored Gemini MCP connectivity, agent cards discoverable again
- **Rationale**: stdio protocol uses stdout as message channel — any noise is a protocol error

### 2026-04-07: Repository Structure Repair (L270-L272)
- **Context**: 13.47 GiB repo blocked git push; structural corruption in tree objects (empty filenames)
- **Decision**: Use `git-filter-repo` for history DAG rebuild (not git filter-branch), purge luma_speedrun_BACKUP (9.7GB) + aimo.tar.gz (4.2GB) uncompressed archives
- **Outcome**: Repository restored to pushable state
- **Rationale**: Repo size bloat is a thermodynamic constraint — high entropy prevents Work Precipitation (git push)

### 2026-04-07: Luma AMD Speedrun — Competition Closure (L265-L268)
- **Context**: Competition ended April 7, 2026 07:59 UTC. Final gaps: GEMM 3.1x, MLA 3.6x, MoE 2.2x
- **Decision**: Archive competition results in `.claude/rules/luma-kernels.md`; K-Search loop and TDD-first GPU kernel patterns are permanent additions
- **Outcome**: K-Search pipeline operational (Ollama synthesis→popcorn eval→tree learning). TDD-first verified e8m0/MFMA data flow locally before spending rate-limited submissions
- **Rationale**: Fused quant+GEMM correctness proven (0.0 error on all 4 shapes). Path forward requires MFMA-native vectorized quantization, not scalar loops

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

## Active Context (Session 91, 2026-04-08)

**Branch**: `main`
**Recent Sessions (86-90)**:
- S86: Cruft cleanup (867 tracked files removed), Makefile targets (train/evaluate/benchmark/demo), .gitignore hardening
- S87: Luma AMD Speedrun deep breakthroughs — stream-aware HIP kernels, continuous evolution loop, K-Search operational
- S88: AIMO 3 mathematical reasoning swarm (Diversity+Entropy Voting+Speculative Decoding), H100 Blackwell handshake
- S89: Repository size repair — git-filter-repo for structural corruption, 13.47 GiB bloat purged
- S90: MCP infrastructure — YAML frontmatter mandatory for AGENTS.md, lazy config for stdio servers, silent stdout rule
**Test Suite**: 6,109 collected
**Genesis Physics/Env Tests**: 357 passing, 1 failing (TestTraining::test_training_updates_metrics in test_jepa_world_model.py)
**Coverage**: ~21%
**Ruff**: 3,378 errors (regression from new code in S87-90 — run `make format && make lint` to fix)
**Known Issues**:
- Full `pytest tests/` segfaults during execution (C extension crash in torch._C or scipy). Collect-only works (6,109 collected). Genesis-specific suite runs clean. Workaround: run module-scoped tests (`uv run pytest tests/physics/ tests/compound/ -q`)
- SurrealDB genesis schema drift: `genesis_schema.surql` defines 14+ fields but live DB has only 7 (never re-applied after SurrealDB 3.0 migration). `prompt_artifacts` inserts fail on required `confidence` field.

**Next Steps**:
1. Fix JEPA training metrics test failure (`test_jepa_world_model.py::TestTraining::test_training_updates_metrics`)
2. Run `uv run ruff check src/cohezion/ --fix` to address 1,632 auto-fixable lint errors
3. Re-apply genesis schema: `surreal import --conn ws://localhost:8001 --user root --pass root --ns cohezion --db genesis src/cohezion/knowledge_graph/genesis_schema.surql`
4. A2A agent cards — zero agent discovery despite 7 specialist agents defined
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
