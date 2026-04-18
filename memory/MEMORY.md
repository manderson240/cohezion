# Cohezion Compiled Memory

**Auto-compiled from `~/vaults/cohezion-vault/` - Query vault for full context**

**Last Updated**: 2026-04-18 (Session 103 retrospective — `cohezion.inference` + 8 adversarial-review follow-ups)

---

## Recent Decisions (Last 7 Days)

### 2026-04-18: Inference Fleet Sprint + All 8 Adversarial-Review Follow-Ups (L359-L366)
- **Context**: `sorted-churning-toucan` sprint shipped `cohezion.inference` (route/extend_claude/TieredOrchestrator/HarnessPool/gaia_adapter) with 3 V-model AutoHarnesses; adversarial review flagged 20+ issues, 6 critical fixed in-session; 8 remaining "Now"-horizon items open on `docs/ROADMAP.md`
- **Decision**: Execute all 8 follow-ups across 2 sessions; land as two focused commits on `isolated/session-oom-modularity` rather than one squash, so the "sprint" and "fix cycle" are reviewable separately
- **Outcome**: `2cbc4d17f` (sprint + 3 P0s, 36 files, 5,692 lines, zero BMAD churn) and `00d1be0b8` (5 P1/P2s, 6 files, +181/-28). Tests 41→45, V-model invariants 25→27. Cherry-pick-onto-fresh-branch path drafted for landing on `main` without dragging 20 unrelated commits from `isolated/...`
- **Rationale**: Surgical git-add sequence (HANDOFF enumeration, no wildcards) preserved clean commit narrative against 1,383-change working tree. Each follow-up had a regression test OR a harness invariant — no "fixed but unverified" items.

### 2026-04-17: Claude Code Native Installation + MCP Cleanup (L359 prior)
- Standardize on `~/.local/bin/claude` (installer). Uninstall npm global. `autoUpdates: true` in settings. Disable official plugin versions when project `.claude/mcp.json` conflicts. Diagnostic: `claude doctor`.

### 2026-04-08: Infrastructure Hardening Sprint (L276-L280)
- **Context**: Three stale items from Session 91 retrospective: schema drift, L183 persistence unwired, segfault/hang suite
- **Decision**: Three teams of specialist agents (schema-fixer, persistence-wirer, segfault-hunter)
- **Outcome**: (1) All 6 genesis tables restored + SurrealDB 3.0 syntax fixed in surql. (2) Steps 9.1+10.7 wired in executor.py — 586 prompt_artifacts + 578 universe_snapshots populated. (3) Segfault root cause found (torch._C + scipy BLAS conflict); anyio hangs fixed (ResourceMonitor heartbeat teardown). Full suite now runs to completion.
- **Rationale**: Compound engineering — each fix unblocked the next. Schema before persistence before metrics.

### 2026-04-08: neurons/synapses ≠ genesis persistence (L280)
- **Context**: Graph HIHO = 0.000 even after L183 wiring
- **Decision**: Document separation: `neurons`/`synapses` = vault-keeper domain; `prompt_artifacts`/`universe_snapshots` = genesis executor domain
- **Outcome**: Graph HIHO requires vault-keeper to run and populate nodes from Obsidian vault — separate work item
- **Rationale**: Two distinct SurrealDB graphs; conflating them prevents correct diagnosis

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

## Active Context (Session 103, 2026-04-18)

**Branch**: `isolated/session-oom-modularity` (two unlanded commits: `2cbc4d17f`, `00d1be0b8`)
**Recent Sessions (97-103)**:
- S97: Hybrid swarm (Gemini+Ollama context tiering), Lemonade embeddable, topological PIVOT. L300-L303
- S98: Autonomy Engine (HIHO-gated MCP tools), A2A async workforce, OMEGA Distiller. L317-L323
- S99: V-Model for AI swarms, autoresearch overnight daemon. L310-L311
- S100: AIMO InferenceServer gateway fix, Mamba-SSM side-loading. L330-L332
- S101: Git LFS migration (14GB→182MB), settings.json schema validation, Entire.io cleanup. L333-L338
- S102: Retrospective — SurrealDB crash-loop fixed, Claude Code npm→native, metrics reconciled
- **S103**: `cohezion.inference` sprint + all 8 "Now" horizon adversarial-review follow-ups. Tests 41→45 in `tests/inference/`, V-model 25→27 invariants (+O3b +I2b). L359-L366
**Test Suite**: 6,369+ collected. Inference subsuite: 45/45. V-model: 27/27 invariants across phases 1+2+6.
**Genesis Tests (physics+world_model+environments)**: 398 passing
**SurrealDB**: 17 tables on port 8001 (SurrealKV). Graph HIHO requires vault-keeper population cycle
**Skills**: 235 definitions (215 PRIME), registry has 133 entries (stale)
**A2A Discovery**: `GET /agents` returns all 7 specialist agents
**Claude Code**: v2.1.112 (native installer at `~/.local/bin/claude`)

**Open loose ends from S103**:
1. `.git/hooks/pre-commit.disabled` still present (policy-blocked my cleanup `rm`) — user action required
2. Push `isolated/session-oom-modularity` to origin (user-gated, shared-state)
3. Cherry-pick `2cbc4d17f` + `00d1be0b8` onto fresh `feat/inference-fleet` off `main`, open PR
4. `docs/ROADMAP.md` "Near (2 wks)" horizon: full n=20 benchmark (needs `systemctl restart lemonade-server`), TurboQuant NPU activation, Anthropic Advisor Tool wiring, root archaeology execution

**Carry-over from S102**:
1. Populate vault neurons/synapses from Obsidian vault (vault-keeper cycle) to restore Graph HIHO
2. Update skill_registry.json to reflect 235 skills (currently 133)
3. Add `ExecStartPre=/usr/bin/mkdir -p /tmp/surrealdb` to surrealdb.service unit for crash resilience
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

**Token Budget**: This file is ~170 lines (target <200). For full history, query `~/vaults/cohezion-vault/`.
