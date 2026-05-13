# Precision Import Graph Wiring Audit

**Date:** 2026-05-02
**Method:** BFS reachability from 3 entry points; no text heuristics

## Summary

| Metric | Count | Rate |
|--------|-------|------|
| Total Python source files | 1,129 | 100% |
| Reachable from entry points | 249 | 22.1% |
| **True orphans** | **880** | **77.9%** |
| Prior text-scan estimate | 466 | 43.6% |
| Wired-but-unreachable (orphans that import cohezion.*) | 426 | — |

**Finding:** The text-scan severely *undercounted* orphans. True orphan rate is **77.9%** (880 modules), not 43.6% (466). The entry-point reachability set is shallower than assumed — only 249 of 1,129 modules are reachable via BFS from the 3 canonical entry points.

## Entry Points Used

1. `src/cohezion/__main__.py` — CLI entry point
2. `src/cohezion/api/__init__.py` — FastAPI application
3. `src/cohezion/compound/executor.py` — Compound engineering engine

## Orphan Distribution by Directory

| Directory | Orphan Modules |
|-----------|---------------|
| `compound/` | 94 |
| `mcp/` | 92 |
| `competition/` | 68 |
| `swarm/` | 67 |
| `api/` | 34 |
| `flume/` | 33 |
| `core/` | 32 |
| `skills/` | 29 |
| `inference/` | 28 |
| `security/` | 27 |
| `integrations/` | 26 |
| `agents/` | 25 |
| `universe/` | 20 |
| `config/` | 15 |
| `platform/` | 14 |
| `arc/` | 14 |
| `knowledge_graph/` | 13 |
| `research/` | 12 |
| `physics/` | 12 |
| `simulation/` | 12 |

## Top 10 Largest Orphans (Highest-Value Wiring Targets)

| Lines | Path | Priority |
|-------|------|----------|
| 2,291 | `src/cohezion/arc/transforms.py` | HIGH — ARC Prize track |
| 1,474 | `src/cohezion/skills/cohezion_mcp.py` | HIGH — MCP skill hub |
| 1,115 | `src/cohezion/universe/capability_eval.py` | HIGH — eval infra |
| 1,075 | `src/cohezion/competition/nemotron_solver/solve.py` | HIGH — Nemotron submission |
| 1,065 | `src/cohezion/security/attack_patterns.py` | MEDIUM — security layer |
| 959 | `src/cohezion/patterns/hermetic_design_patterns.py` | LOW — patterns ref |
| 938 | `src/cohezion/universe/agentic_env.py` | HIGH — RL environment |
| 935 | `src/cohezion/compound/evolution_training_bridge.py` | HIGH — compound loop |
| 920 | `src/cohezion/cli/main.py` | HIGH — CLI completeness |
| 913 | `src/cohezion/reliability/quantum_performance_monitor.py` | MEDIUM — observability |

## Top 5 "Wired But Unreachable"

Modules that import `cohezion.*` (indicating intent to integrate) but are not reachable from any entry point. These already reference cohezion internals and need only be *imported* somewhere in the call graph to activate.

| Lines | Path | Cohezion Imports |
|-------|------|-----------------|
| 1,474 | `src/cohezion/skills/cohezion_mcp.py` | 9 modules (agents.daily_scout, reliability.batch_manager, …) |
| 935 | `src/cohezion/compound/evolution_training_bridge.py` | 2 modules (compound.group_evolution, flume.experience_encoder) |
| 920 | `src/cohezion/cli/main.py` | 12 modules (config, core.persistence.*, compound.executor, …) |
| 867 | `src/cohezion/platform/daily_health_digest.py` | 5 modules (core.persistence.surreal_client, platform.*, …) |
| 863 | `src/cohezion/benchmarks/benchmark_suite.py` | 1 module (compound.journey_analyzer) |

## Recommended Wiring Priority Order

### Priority 1 — CLI completeness (immediate, low risk)
**`src/cohezion/cli/main.py`** (920 lines, 12 imports)
Already imports from `compound.executor`, `config`, `core.persistence.*`. Wire by importing it in `src/cohezion/__main__.py`'s CLI dispatch path. Activates the entire CLI subgraph (estimated 50–80 transitively reachable modules).

### Priority 2 — Compound loop post-execution (high compound-engineering value)
**`src/cohezion/compound/post_execution.py`** (797 lines, 9 imports)
Imports `executor`, `design_review_report`, `inflection_detector`, and 6 others — all already in the reachable set or high-priority orphans. Wire from `compound/executor.py` as a post-step hook. Closes the compound loop for post-execution retrospection.

**`src/cohezion/compound/evolution_training_bridge.py`** (935 lines, 2 imports)
Bridges `group_evolution` ↔ `flume.experience_encoder`. Both dependencies are accessible. Wire from `CompoundExecutor.__init__` or `executor_factory.py`.

### Priority 3 — Skills/MCP activation (unlocks 29 skill-related orphans)
**`src/cohezion/skills/cohezion_mcp.py`** (1,474 lines, 9 imports)
Central MCP skill hub with 9 cohezion imports already in place. Wire from `src/cohezion/mcp/registry.py` (already reachable via `api/__init__.py`). Estimated downstream: 20–30 additional reachable skill modules.

## Notes on Text-Scan Discrepancy

The text scan (466 orphans, 43.6%) used pattern matching for import keywords without resolving which modules were already transitively reachable. The BFS audit revealed the reachable set is much smaller (249 modules, 22.1%) than the text scan assumed, yielding 880 true orphans. The discrepancy (880 − 466 = 414 modules) represents modules the text scan incorrectly classified as "wired" because they contained `from cohezion.*` imports but were never themselves imported from a reachable path.

## Methodology

BFS starting from 3 entry points, following `from cohezion.X import` and `import cohezion.X` patterns. Module resolution: `cohezion.a.b.c` → `src/cohezion/a/b/c.py` or `src/cohezion/a/b/c/__init__.py`. Conditional imports (inside `try:` / `if TYPE_CHECKING:`) are included in the graph since they represent real runtime dependencies.
