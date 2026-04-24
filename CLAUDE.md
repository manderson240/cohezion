# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Cohezion - Compound AI Orchestration

COHEZION: 12D agentic universe with FLUME VAE, compound engineering, multi-agent swarm, and autonomous skill refinement. **Governed by Constitution (`.agent/CONSTITUTION.md`) and Charter (`.agent/COHEZION_CHARTER.md`).**

## Token-Efficient Essentials

### ⚡ Core Commands
```bash
uv run pytest tests/ -q              # Full test suite (6,133 tests collected)
uv run pytest tests/compound/ -v     # Run module tests
uv run pytest tests/test_*.py::name  # Single test
make validate                         # Compound loop validation (23 checks, ~18s)
make format && make lint && make all # Check → fix → verify
```

### ⚡ Security Standards (MANDATORY)
```bash
# NEVER print, echo, or display any passwords or secrets
# NEVER store SUDO_PASSWORD in .env for scripts - use passwordless sudo
# NEVER write secrets to temp files that persist

# ALWAYS use 'uv' for package management - NEVER bare 'pip' or 'pip install'
uv pip install package              # Install package
uv venv && source .venv/bin/activate && uv pip install -e .  # New project setup

# For sudo: configure passwordless sudo for automation OR run interactively
# Do NOT attempt to parse .env for SUDO_PASSWORD - this is a security risk
```

### ⚡ Git LFS & Repo Health (L333-L337, Session 101)
```bash
# Git LFS is active — .gitattributes tracks: *.so, *.whl, *.pt, *.pth, *.pkl, *.tar.gz, *.bundle, *.jsonl
# LFS files are POINTERS in git (~130 bytes), actual content in .git/lfs/objects/
# Bundle size: 182MB (was 14GB before LFS migration)
# Remote: git@github.com:manderson240/cohezion.git

# MANDATORY: Never commit large binaries without LFS
# Pre-commit hook `lfs-pointer-check` enforces this automatically
# If LFS breaks: git lfs install && git add --renormalize .

# MANDATORY: Run monthly — entire/ shadow branches accumulate fast
# entire clean --all --dry-run   # preview orphaned branches
# entire clean --all --force     # delete them

# SessionStart hooks enforce:
# - settings.json schema validation (L333: invalid fields disable ALL settings silently)
# - repo-health-check: .git/ size, entire/ branch count, remote configured, LFS active, fsck clean
```

### ⚡ MCP stdio Server Rules (L273-L275, Sessions 89-90)
```python
# MANDATORY: Agent MARKDOWN files (AGENTS.md) must start with valid YAML frontmatter
# Missing `name` + `description` = silent failure — entire capability set goes dark
# ---
# name: my-server
# description: What this server does
# ---

# MANDATORY: Config lookups in MCP servers must be LAZY (not at module import time)
# Slow external checks (e.g., Bitwarden vault) at startup exceed CLI handshake timeout
# WRONG:  SECRET = get_vault_secret()           # runs at import → timeout
# RIGHT:  def get_secret(): return get_vault_secret()  # lazy, called on first use

# MANDATORY: stdio MCP servers must be SILENT on stdout during initialization
# stdout is the message channel — any debug output corrupts the protocol stream
# Use: .venv/bin/python server.py   OR   uv -q run server.py  (suppress uv update msgs)
# NEVER: logger.info("Starting...") at module scope, print() anywhere in init path
```

### ⚡ Critical Principles (Sessions 40-55)
1. **Implement ONE feature, validate manually, write 5 tests** (NOT 600 pre-implementation tests)
2. **Use proven templates** (e.g., cloud-vault-mcp: 40+ tools) over greenfield exploration
3. **Mock live services at source**: `@patch("cohezion.swarm.compound_client.get_compound_client")`
4. **Report honest metrics** (98.8% beats inflated 100% for decision-making)
5. **Never write infrastructure for products that don't exist**

### ⚡ Execution Priority (Sessions 56+)

**EXECUTE FIRST. PLAN SECOND. INFRASTRUCTURE NEVER (unless explicitly requested).**

When given a task:
1. **Can you execute it RIGHT NOW with existing tools?** If yes, do it. No planning phase needed.
2. **Does it need a plan?** Only if 10+ files or architectural. Ask user if they want `/spec`.
3. **Are you building a helper/framework/tool?** STOP. Re-read the original task. Build the deliverable, not tools to build the deliverable.

**Session budget:** If >30 minutes have passed without producing a runnable artifact (code change, submission, commit), you are in infrastructure drift. STOP and deliver something concrete.

**Evidence of drift (any one = STOP):**
- Creating a new class/module not in the original request
- Writing >100 lines of "framework" code before the first test passes
- Researching dependencies for a tool you are building to build the actual thing
- The phrase "first we need to set up..." when the thing already exists

### ⚡ Vault-First Knowledge Management (NEW: Session 56)

**CRITICAL**: All session learnings MUST be logged to vault, not MEMORY.md directly.

**MEMORY.md = Compiled Cache** (auto-generated weekly):
- 95 lines (vs 1177 lines old version)
- Recent decisions (last 7 days)
- Most-used patterns (top 10)
- Quick reference only

**Vault = Single Source of Truth**:
- `~/vaults/cohezion-vault/` (150+ decisions, patterns, experiments)
- Searchable via `vault_find_relevant_context(query)`
- Survives across sessions, compounds knowledge

See skill: `cohezion-vault-workflow` for vault API examples (log decisions, experiments, patterns) and MEMORY.md regeneration.

### ⚡ Architecture at a Glance
| Layer | Components | Entry |
|-------|-----------|-------|
| **Compound** | Executor, SkillRefiner, RetrospectionEngine, JourneyTracker, DRRGenerator, TapeLogger | `CompoundExecutor` |
| **Swarm** | TeamOrchestrator, ExecutionOrchestrator, DynamicModelRouter | `TeamExecutor` |
| **Cache** | SemanticCache (L1 hash + L2 cosine + L3 vault, 95%+ hit rate) | `SemanticCache` |
| **Cost Opt** | CostAwareRouter (Lemonade-first, YAML profiles, 45 models), BudgetEnforcer, ModelQualityClassifier | `CostAwareRouter` |
| **Persistence** | SessionPersistence (vault + JSONL), MetricsCollector, DegradationDetector, ExecutionTraces (Meta-Harness L225) | `SessionManager` |
| **Physics** | SU(2) Spinors, Riemannian/Lagrangian, FiberBundle, GaugeTheory, Fisher metric | `SpinorState` |
| **World Model** | JEPA predictor (86K params, causal masking), Cosmogony, SymmetryBreaking | `JEPAWorldModel` |
| **Bioelectric** | Levin bioelectric network, gap junction percolation, HIHO phase transition | `BioelectricNetwork` |
| **Natural Capital** | InVEST habitat quality model, HIHO proximity as habitat quality | `NaturalCapitalModel` |
| **Evo Model** | Agents-as-EVOs physics, evolutionary dynamics on manifold | `EvoModel` |
| **Worldviews** | 16 indigenous traditions x 10 cosmogony steps, Worldview Explorer | `WorldviewExplorer` |
| **Ouroboros** | Ouroboros bridge + Mycelium network wired into Genesis chain | `OuroborosBridge` |
| **Environments** | ManifoldEnv (gymnasium, 19D obs, verifiable rewards), SwarmEnv (multi-agent gauge coupling) | `gym.make('Cohezion/ManifoldEnv-v0')` |
| **Governance** | AutonomyEngine (cosmogonic tiers), ConciergeAgent, KnowledgeBridge, FlumeBridge | `AutonomyEngine` |
| **Data Mesh** | DataProduct (typed SLA), MCP Registry (tier access control + call tracking). Canonical: `src/cohezion/data_mesh/`. NOTE: orphan `src/cohezion/datamesh/` (no underscore) is slated for deletion per ORPHAN_AUDIT_2026_04_23. | `get_cohezion_data_products()` |
| **Providers** | LemonadeProvider (local 3-slot), OllamaCloudProvider ($20/mo), LemonadeAdapter (NPU/GPU/CPU hotswap) | `CostAwareRouter` |
| **Genesis UI** | 11 components across 8 tabs: BlochSphere, GenesisScene, FlumeLatentViz, SwarmTopologyViz, etc. | `/genesis` route |
| **Knowledge** | Vault-First (decisions/patterns/experiments), auto-compiled MEMORY.md | `vault_find_relevant_context` |
| **Anthropic Intel** | 11-source monitor, version-watch hook, `/anthropic-scan`, risk-tiered auto-integration | `/anthropic-scan` |

### ⚡ Agent Protocol Stack (6-Protocol Architecture)
| Protocol | Purpose | Cohezion Status |
|----------|---------|----------------|
| **MCP** | Agent ↔ Tool connectivity | **Strong** (87+ tools via cloud-vault-mcp, compound-mcp, maintenance-mcp) |
| **A2A** | Agent ↔ Agent discovery/coordination | **In Progress** (7 specialist agents with agent cards) |
| **UCP** | Commerce lifecycle | N/A |
| **AP2** | Payment authorization | N/A |
| **A2UI** | Agent ↔ UI composition | **Strong** (8-component catalog, declarative experience scripts, A2UIRenderer) |
| **AG-UI** | Event streaming transport | **Strong** (typed SSE events, /api/agui/stream, 15+ event types) |

### ⚡ Platform Coordination
| Specialist | Role | Format |
|-----------|------|--------|
| `vault-keeper` | Vault health, orphan detection, frontmatter enforcement | Agent + PRIME |
| `surreal-dba` | Schema validation, index optimization, graph health | Agent + PRIME |
| `claude-specialist` | Claude Code/API optimization, agent teams | Agent + PRIME |
| `gemini-specialist` | Gemini CLI, Google ADK, ecosystem integration | Agent + PRIME |
| `ollama-specialist` | Local model lifecycle, VRAM, DynamicModelRouter | Agent + PRIME |
| `mcp-specialist` | MCP server lifecycle, tool schemas, health monitoring | Agent + PRIME |
| `platform-coordinator` | Cross-platform routing, cost tiers, fallback chains | Agent + PRIME |

**Cost routing tiers**: 70% simple (Ollama/Flash-Lite, free) → 20% medium (Sonnet, $3/M) → 10% hard (Opus, $15/M)

### ⚡ Quick Reference
- **Language**: Python 3.13+ | **Package Manager**: `uv` (never bare python)
- **DB**: SurrealDB (ws://localhost:8001) | **API**: FastAPI :8080
- **Tests**: 6,133 collected (verified 2026-04-23 post-synthetic-sniffing-panda; 4 collection errors in swarm/cache test files), full suite completes without crash. Genesis: 398 (physics 309 + world_model 34 + environments 55). Physics: 22 conservation + 15 invariant checker. LeWM JEPA: 34. GraphRAG: 12. DRR generator: 15. Constitutional enforcer: 13. Verifiable rewards: 4. | **Coverage** (post-campaign hot files): executor.py 51%, cost_aware_router.py 88%, knowledge_graph/ 53% | html report in `htmlcov/`
- **SurrealDB Persistence**: SurrealKV backend (migrated from RocksDB Session 96b) with `?versioned=true` for VERSION clause temporal queries. Port 8001, 127.0.0.1 only. Bi-temporal schemas (valid_from/valid_to) on neurons, agent_journey, universe_node. V-Model tables: vmodel_gate, traces, hash_chain, proof_obligation (Session 96b). Hash-chain audit trail in JourneyTracker (OLIF mitigation).
- **CI**: `make lint-check && uv run pytest` before commit
- **Entry point**: `cohezion = "cohezion.__main__:main"`
- **Vault**: `~/vaults/cohezion-vault/` — Query via `vault_find_relevant_context(query)`
- **Git LFS**: Active (46 files: vendor/*.so, *.whl, *.pth). Bundle: 182MB. Remote: `manderson240/cohezion`
- **Repo Health**: SessionStart hooks validate settings.json schema + check .git/ size, branch count, LFS, remote, fsck

## The Compound Engineering Loop (Production-Ready)

```
PRIME Skill (markdown)
  ↓
InstructionExpander (parse → tasks)
  ↓
PlanExecutor (tactical plan)
  ↓
ExecutionOrchestrator (execute with 11-step pipeline)
  ├─ RequestAlignmentAnalyzer (coherence check)
  ├─ GlobalMetricsAggregator (record instance metrics)
  ├─ DegradationDetector (thermal, quality thresholds) → healing/ + resilience/ + CostAwareRouter feedback
  ├─ JourneyTracker (12D universe position) + JEPA surprise + bioelectric percolation → SurrealDB
  ├─ OuroborosBridge (physics coherence check) + Mycelium (change correlation)
  └─ MyceliumRegistry (auto-capture execution patterns for skill synthesis)
  ↓
RetrospectionEngine (extract learnings, flag anomalies, pivot detection)
  ↓
SkillRefiner (update skill definition)
  ↓
SkillConsensusVoter (multi-agent validation)
  ↓
Updated Skill (loop again)
```
**CLI**: `uv run python scripts/drivers/compound_cycle.py` (dry-run) or via `/compound` API endpoint.

## Key Directories (Find Anything Fast)

| Path | Purpose | Key Files |
|------|---------|-----------|
| `src/cohezion/compound/` | Executor, SkillRefiner, RetrospectionEngine, JourneyTracker | `executor.py` (11-step) |
| `src/cohezion/swarm/` | Team orchestration, cost routing, model quality | `team_executor.py`, `cost_aware_router.py` |
| `src/cohezion/cache/` | L1/L2/L3 semantic cache (95%+ hit rate) | `semantic_cache.py` |
| `src/cohezion/skills/` | 235 skill definitions (215 PRIME) (*.md + *.py) | `skill_registry.json` |
| `src/cohezion/persistence/` | SurrealDB, checkpoints, session recovery | `surreal_client.py` |
| `src/cohezion/environments/` | Gymnasium RL envs: ManifoldEnv (single), SwarmEnv (multi-agent) | `manifold_env.py`, `swarm_env.py` |
| `src/cohezion/api/` | FastAPI backend (92 route handlers) | `__init__.py`, `services/genesis.py` |
| `src/cohezion/flume/` | FLUME VAE (256D latent space) | `flume_vae.py` |
| `src/cohezion/physics/` | **Genesis Engine**: SU(2) spinors, Riemannian, Lagrangian, fiber bundles, gauge theory, Fisher metric, cosmogony | `spinor.py`, `cosmogony.py` |
| `src/cohezion/world_model/` | JEPA world model (86K params, causal masking, CPU-trainable) | `jepa_world_model.py` |
| `src/cohezion/world_model/bioelectric_model.py` | Levin bioelectric network, gap junction percolation | `BioelectricNetwork` |
| `src/cohezion/world_model/natural_capital.py` | InVEST habitat quality, HIHO proximity mapping | `NaturalCapitalModel` |
| `src/cohezion/world_model/evo_model.py` | Agents-as-EVOs evolutionary physics | `EvoModel` |
| `src/cohezion/worldviews/` | 16 indigenous traditions x 10 cosmogony steps | `WorldviewExplorer` |
| `src/cohezion/ouroboros/` | Ouroboros bridge + Mycelium network | `OuroborosBridge` |
| `src/cohezion/audio/` | PocketTTS narrator, Kyutai Labs integration | `narrator.py` |
| `src/web/anima_dashboard/` | Next.js 16 + Three.js + Tone.js webapp | `/genesis` route (4 tabs) |
| `tests/conftest.py` | **CRITICAL**: Singleton reset for FLUME VAE, RL policy, loggers | **Read this first** |

## Coding Standards (Cohezion-Specific)

- **FLUME-First**: New modules MUST encode/decode through FLUME. Start with `encode()` → latent reasoning → `decode()`. Don't retrofit — wire from the start (Learning 215)
- **Wire-at-Creation**: New modules MUST declare a wiring target (DegradationDetector, CapabilityMatrix, CompoundExecutor step, or Hookify rule) at creation time. Build-then-forget = 41 orphaned modules (Learning 227)
- **Async**: All I/O must be `async/await` with timeouts. No blocking calls in executors
- **Error handling**: Specific exceptions + circuit breakers (`cohezion.reliability.get_circuit()`). **Anti-pattern (Learning 359)**: `except (SubclassError, Exception)` is a stealth bare-except — because `Exception` is a supertype, the tuple is semantically identical to `except Exception:`. Use only sibling-or-unrelated types in except tuples (e.g. `except (ImportError, AttributeError, KeyError, TypeError, ValueError)`). If you find yourself writing a wide tuple "just to be safe," name the 3-5 types you actually want to silence; let the rest propagate
- **CLI flag verification (Learning 360)**: When adversarial review or any roadmap item prescribes a specific CLI command, run `<cmd> --help | grep <flag>` before implementing. Mental models of CLI APIs drift; `--help` is ground truth. Captured in roadmap entries with explicit correction notes when the prescribed flag is invalid
- **Validation**: Pydantic at boundaries (input/output). Fail fast with assertions
- **Every `src/` dir**: MUST have `__init__.py`. Enables vault skill discovery
- **Observability**: Log state transitions (input → processing → output). Track coherence
- **YAML Frontmatter Markdown**: Structured config/state files that humans may read MUST use YAML frontmatter `.md` (not JSON). Consistent with vault, skills, `.context/` conventions. JSON only for wire formats and machine-to-machine data

## Token Budgets (Conservative Estimates)

| Task | Tokens | Pattern |
|------|--------|---------|
| Implement 1 feature | 500-1,500 | Copy template → code → manual test → 5 tests |
| Research + implement | 2,000-3,000 | Quick survey → proof of concept → tests |
| Full test suite run | 100 | `uv run pytest tests/ -q` (no code changes) |
| Single test debug | 200-500 | Add print → run → check output → fix → verify |
| Skill refinement loop | 1,500-2,500 | Analyze failures → update PRIME skill → retest |
| **ANTI-PATTERN**: Research-first | 5,000-10,000 | 1,200 lines research + 600 tests + 0 implementation = wasted |
| **ANTI-PATTERN**: Infrastructure play | 8,000+ | Dependency research, 4,400 placeholder tests, product doesn't exist |

**Rule**: If feature doesn't exist yet, DON'T build infrastructure. Implement, validate, THEN test.

## Operational Patterns

See skills: `cohezion-debugging-scenarios` for test isolation, singleton resets, and flaky test fixes. See global rules: `tdd-enforcement.md` for mocking patterns, `verification-before-completion.md` for verification protocol.

### ⚡ Measurement Integrity
- **Report actual numbers**: 2,675/2,700 passing (98.1%) > 1,599 passing (inflated)
- **Flag discrepancies**: If independent test shows different count, request re-verification immediately
- **Verify claims**: "Complete" = files exist AND tests pass, not projected

### ⚡ Surgical Commits Against High-Churn Trees (Learning 363)
When the working tree has unrelated churn (BMAD upgrades, pre-existing untracked, other sprints) and you need a clean commit:
- Enumerate paths explicitly in a handoff markdown before staging — no wildcards, no `git add .`
- Verify the staged set with `git diff --cached --name-only | grep -iE "<churn-pattern>"` returning empty before committing
- Prefer two focused commits (feature + follow-ups) over a single squash when the narratives are distinct — cherry-picking to a fresh branch off `main` preserves the separation without dragging unrelated history

### ⚡ V-Model Structural-Before-Behavioral (Learning 366)
Every behavioral invariant whose failure surface is a keyword/signature drift should have a paired *structural* invariant at the harness layer:
- Behavioral test would fail with `TypeError: got unexpected keyword argument` deep in the call stack — hard to diagnose
- Structural check (`inspect.signature(fn).parameters.get(name)`) fires at harness start with an explicit invariant name (e.g. "O3b: fn.run accepts budget_usd kwarg")
- Structural check cost: ~1ms; pays for itself the first time a refactor drifts a signature

### ⚡ Diagnostic Sidecars (Learning 362)
When a summary table truncates diagnostic data AND the failing path is a subprocess that can fail silently, write full stdout+stderr to a sidecar file next to the report. V-Model invariant asserts the sidecar exists when the subprocess had 0 successes. Summary tables are for humans scanning; sidecars are for humans diagnosing.

### ⚡ Adversarial Review in Parallel (INSIGHTS #7)
Spawn 3 concurrent reviewer agents (scientific rigor / edge-case hunting / security) via `Agent` tool in a single message for non-trivial deliverables. Synthesize in main context. Sequential review costs 3× wall-clock and loses cross-pollination; parallel produces a combined review in ~90s + synthesis time. Applied to sprint `sorted-churning-toucan` → 20+ findings, 14 actionable (6 in-session fixes + 3 P0 + 5 P1/P2).

### ⚡ Additive Composition Under Directive Changes (INSIGHTS #11)
When the user redirects mid-sprint (e.g. "now do X instead of Y"), prefer adding a new module over modifying existing tested code. `cohezion.inference` absorbed 4 mid-sprint pivots (TurboQuant → CLI → GAIA → tiered) by growing from 3 to 7 modules without breaking the original 29 tests. Rule: if a new directive would force editing a passing-test surface, first ask "can this be a new module that composes with the existing one?" Compositional additions don't regress behavior; modifications risk it.

### ⚡ Tiered > Flat Routing (INSIGHTS #2)
`route()` is a dispatch primitive; `TieredOrchestrator` is the composition primitive. Flat routing picks one lane; tiered runs cheap-first, escalates only when quality gates fail. Same 4-lane fleet under orchestration delivers quality-bounded cost curves that flat routing can't express. For any "pick the best provider" problem, ask: is this really one-shot, or should cheaper options be tried first and escalated?

## Hardware & Constraints (Strix Halo)

- **CPU**: AMD Ryzen AI MAX+ 395 (16C/32T, AVX-512, AMX) | **GPU**: Radeon 8060S (iGPU, unified memory)
- **RAM**: 128 GiB LPDDR5X | **Storage**: 2TB NVMe + 32GB swap (ZFS)
- **Local Models**: Ollama (deepseek-r1:70b, qwen3-coder:30b, phi3:mini, internlm/intern-s1-mini). **Global limit = 4 concurrent**
- **Cost**: Cloud Run = Free Tier only (no instances when idle). Prefer local Ollama over API calls
- **Truth Anchor**: See `HARDWARE_PROFILE_PRIME.md` (never assume RTX/CUDA)

## Multi-Session Worktree Pattern (MANDATORY)

See skill: `cohezion-worktree-workflow` — covers session scripts (start/end/list_sessions.sh), manual git worktree commands, commit format with Co-Authored-By, and recommended git config.

## Design Principles (Compound-Aligned)

- **HIHO Stability** (50% coherence): Optimal balance between exploitation + exploration
- **Compound Engineering**: Every feature makes future features easier (loop → skill updates → better routing)
- **Observable AI**: Log states before action. Track coherence. Expose confidence. Enable rollback
- **Deterministic Responsibility**: Idempotency keys for all external calls. Replay from checkpoints
- **Expert Domain Lattice**: Route complex requests through specialist agents (Architect, Engineer, Biologist, QHW, QAlgo)
- **SPIN Coherence**: Information unit = Rotation + Precession. Alignment when phases match

## Critical References (Read First)

| Document | Purpose | Key Insight |
|----------|---------|------------|
| `tests/conftest.py` | **TEST ISOLATION** | FLUME VAE + RL policy + logger resets prevent flaky tests |
| `.agent/CONSTITUTION.md` | **HARD CONSTRAINTS** | No WMD/infrastructure attacks. Honesty mandatory. Idempotency required |
| `.agent/COHEZION_CHARTER.md` | **DESIGN THEORY** | SPIN, FLUME, HIHO, Expert Domain Lattice |
| `HARDWARE_PROFILE_PRIME.md` | **TRUTH ANCHOR** | Never assume RTX/CUDA. AMD Ryzen AI MAX+ 395 only |
| `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` | **LESSONS EXTRACTED** | Historical patterns, anti-patterns, cost lessons |
| `.claude/rules/git-workflow.md` | **GIT PATTERNS** | Conventional commits, branch naming, PR targets |
| `.claude/rules/testing.md` | **TEST RULES** | Avoid `walk_packages`, mock at source, HIHO invariant |
| `cloud-vault-mcp/` | **MCP TEMPLATE** | 40+ tools, FastMCP proven. Copy when building MCP servers |
| `src/cohezion/physics/observer_patch.py` | **OPH BRIDGE** | Observer Patch Holography axioms → SPIN coherence. FloatingPragma (Apache 2.0) |
| `src/cohezion/data_mesh/data_product.py` | **DATA MESH** | Typed data products with SLA for 17+ MCP servers. Dehghani (2022) |
| `src/web/anima_dashboard/src/a2ui/` | **A2UI CATALOG** | 9 declarative components + experience scripts. Google A2UI v0.9 (Apache 2.0) |
| `src/cohezion/api/agui_events.py` | **AG-UI EVENTS** | 15+ typed SSE event types. CopilotKit AG-UI (Apache 2.0) |

## Agent Journey Tracking & Request Alignment

See skill: `cohezion-journey-tracking` — covers JourneyTracker API (record_state, record_transition, save_checkpoint, rollback), RequestAlignmentAnalyzer (coherence/completeness/drift-risk), and alignment anti-patterns.

## Metrics & Observability (Production Monitoring)

See skill: `cohezion-metrics-observability` — covers GlobalMetricsAggregator (record_execution, get_metrics_snapshot, get_skill_metrics), BudgetEnforcer (monthly budget checks, token control), and cost tracking.

## Data Storage Architecture for Simulations

See skill: `cohezion-data-governance` — covers three-tier storage (Git/SurrealDB/External), pre-commit hook for >50MB files, JourneyTracker artifact registration, deterministic recovery, and success metrics.

---

## Common Debugging Scenarios

See skill: `cohezion-debugging-scenarios` — covers test isolation/singleton pollution, flaky tests with random seeds, Ollama timeouts, journey tracking silent failures, and token count mismatches.

## Skill Routing

See skill: `cohezion-skill-routing` for the decision tree, keyword-to-skill routing table, and overlap resolution guide. When in doubt: `bmad-help`.

## Quick Lookup

| Need | Command | File |
|------|---------|------|
| Run tests (all) | `uv run pytest tests/ -q` | `pytest.ini` |
| Run tests (module) | `uv run pytest tests/compound/ -v` | `tests/conftest.py` |
| Format + lint | `make format && make lint` | `Makefile` |
| Check types | `make type-check` | `pyproject.toml` |
| Start API | `uv run uvicorn cohezion.api:app --reload` | `src/cohezion/api/__init__.py` |
| Find skill | `grep -r "skill_name" src/cohezion/skills/` | `skill_registry.json` |
| Debug journeys | `JourneyTracker.get_journey(agent_id)` | `src/cohezion/compound/journey_tracker.py` |
| Check alignment | `RequestAlignmentAnalyzer.analyze(...)` | `src/cohezion/compound/request_alignment_analyzer.py` |
| Anthropic scan | `/anthropic-scan` | `~/.claude/commands/anthropic-scan.md` |
| Config audit | Read `~/.claude/anthropic-intel/latest-digest.md` | `~/.claude/anthropic-intel/` |

## Kaggle Blackwell Handshake (Critical)
When orchestrating jobs on Kaggle G4 (Blackwell) infrastructure, standard `accelerator` requests will fail. You MUST follow this handshake:
1.  **Metadata**: Set `"machine_shape": "NvidiaRtxPro6000"` and `"dockerImageVersionId": 31287` in the internal `.ipynb` metadata.
2.  **Environment**: Copy the `nvidia_utility_script` to `/tmp` and `chmod +x` the `ptxas-blackwell` binary.
3.  **Triton**: Set `os.environ["TRITON_PTXAS_PATH"]` to the `/tmp` binary path.
4.  **Auth**: Pre-authorize models in the `"model_sources"` metadata array.
