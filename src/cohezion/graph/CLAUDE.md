# graph — Local Context

This file loads in addition to the root `CLAUDE.md`. Root applies here too.

**Purpose:** Graph execution engine for DAG-native multi-agent workflows. Inspired by MASFactory's graph-centric composition model, adapted for Cohezion's compound engineering stack with SurrealDB persistence.

## Entry points (5 modules)

| Module | Key class(es) | LOC |
|---|---|---|
| `builder.py` | `WorkflowBuilder` | 75 |
| `engine.py` | `WorkflowEngine` | 376 |
| `nodes.py` | `WorkflowNode`, `AgentNode`, `ToolNode` | 191 |
| `persistence.py` | `WorkflowPersistence` | 136 |
| `types.py` | `NodeStatus`, `NodeSpec`, `EdgeSpec` | 187 |

## Invariants / notes referencing this package (from harness.md / root CLAUDE.md)

- | `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` | **LESSONS EXTRACTED** | Historical patterns, anti-patterns, cost lessons |

_Seeded 2026-07-22, HAND-MAINTAINED since — there is no generator. The original note credited a `gen_nested_claude.py` that exists in no commit and nowhere on disk; corrected 2026-07-31 so nobody hunts for it or assumes a regeneration will clear drift. Update this file in the same commit as the code. Guarded by `scripts/ci/doc_code_consistency.py`: E1/E2 that every path and module reference resolves, E5 that the declared module count matches the package._
