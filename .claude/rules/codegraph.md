# Codebase Graph — read the artifact, don't re-derive it

The cohezion repo ships a precomputed **import + inheritance dependency graph** so a
session can understand the code's structure in one read instead of parsing ~1400 files
every time. A project SessionStart hook (`scripts/codegraph/codegraph-watch.sh`) emits one
of three signals.

## Triggers

### `[codegraph:ready] <path>`
The artifact exists and matches the current HEAD. **Before doing any structural work**
(finding where a feature lives, judging blast radius, spotting orphans, planning a refactor),
read `<path>` — a small JSON with:

- `import_spine` / `authorities` — the most-depended-on modules (the foundations).
- `hubs` / `orchestrators` — the wiring / integration points.
- `abstraction_spine` — the class-inheritance roots (a DIFFERENT spine than imports: the
  agent/type hierarchy, invisible to import analysis).
- `communities` — Louvain clusters (the EMERGENT architecture; note it does NOT match the
  folder tree — modularity ~0.76, all clusters mixed).
- `isolated_count` — import-isolated modules. **Isolation is NOT death**: many are
  entry-points, string-loaded skills, or reachable via scripts/tests/dynamic imports the
  static graph can't see. Treat the orphan set as a hypothesis, never a delete list
  (`~/.claude/rules/non-destructive-wiring.md`).

Narrative map with the findings: `~/vaults/cohezion-vault/reports/20260828-codebase-import-graph-map.md`.

### `[codegraph:stale] <path> (generated at <a>, HEAD now <b>)`
The artifact still exists and is ~95% accurate — READ IT anyway; the spine and subsystems
rarely move commit-to-commit. Regenerate ONLY if your task depends on the graph being exact
(a structural audit, a large refactor):

    python scripts/codegraph/build_graph.py --print   # ~a few seconds; rewrites the artifact

Do NOT regenerate reflexively on every stale signal — that is wasted compute for a graph
that barely changed. To inspect without touching the cached artifact:

    python scripts/codegraph/build_graph.py --dry-run  # build + summary, writes nothing

### `[codegraph:absent]`
No usable artifact (missing, or a JSON without a `head_sha`). Generate it once:

    python scripts/codegraph/build_graph.py

## Why this exists

Every session that needed to understand the codebase was re-parsing it from scratch. The
graph is deterministic and $0 to compute but not free to recompute per session; caching it
as an artifact in the vault (`~/vaults/cohezion-vault/graph/codegraph.json` — untracked,
outside the repo) + a read-only staleness signal lets sessions build on the last one's
work. The generator, hook, and this rule are the three consumed pieces — the artifact is
read, the hook fires the signal, this rule turns the signal into an action.

Method / research lineage (RepoGraph, Code Graph Model, LocAgent, Codebase-Memory, 2026):
the map report's "v2 enhancement" section. Next edge to add when needed: `invokes` (the call
graph) — highest-value remaining, but needs dynamic-dispatch handling, so build it as a
grounded pass, don't approximate.
