# Agent Write Surfaces (exclusive-ownership map)

Adopted from github.com/cbrock84/headcount: **every repository path must resolve
to exactly ONE owning agent.** A topic split has no checkable boundary; a
write-surface split does. This map is the checkable boundary.

Resolution rules (enforced by `scripts/ci/check_agent_surfaces.py`):

- Longest matching glob wins (specificity beats breadth).
- A specificity tie between **different** owners is an error.
- A path matching no row is an error (fail-closed): add a row rather than
  letting ownership drift.
- Delegation charters must quote the owning surface for every file a child
  may touch; a child editing outside its surface is a failed review.

| glob | owner |
|---|---|
| `AGENT-SURFACES.md` | @docs-keeper |
| `AGENTS.md` | @docs-keeper |
| `CLAUDE.md` | @docs-keeper |
| `docs/**` | @docs-keeper |
| `src/cohezion/skills/**` | @docs-keeper |
| `.github/**` | @ci-governance |
| `scripts/ci/**` | @ci-governance |
| `scripts/hooks/**` | @ci-governance |
| `pyproject.toml` | @ci-governance |
| `uv.lock` | @ci-governance |
| `tests/property/**` | @ci-governance |
| `tests/mutation/**` | @ci-governance |
| `tests/contracts/**` | @ci-governance |
| `tests/fuzz/**` | @ci-governance |
| `scripts/ops/**` | @ops-fleet |
| `scripts/maintenance/**` | @ops-fleet |
| `config/**` | @ops-fleet |
| `src/cohezion/__main__.py` | @ops-fleet |
| `scripts/kaggle/**` | @research-daemon |
| `src/cohezion/competitions/**` | @research-daemon |
| `submissions/**` | @research-daemon |
| `scripts/lanes/**` | @research-daemon |
| `scripts/stealthskater_ingest.py` | @research-daemon |
| `src/cohezion/researcher/**` | @research-daemon |
| `src/cohezion/flume/**` | @research-daemon |
| `src/cohezion/platform/**` | @platform-gate |
| `tests/platform/**` | @platform-gate |
| `src/cohezion/inference/**` | @inference-fabric |
| `tests/inference/**` | @inference-fabric |
| `src/cohezion/cache/**` | @inference-fabric |
| `src/cohezion/reliability/**` | @inference-fabric |
| `tests/unit/test_delegation_logger.py` | @inference-fabric |
| `src/cohezion/swarm/**` | @swarm-pool |
| `tests/swarm/**` | @swarm-pool |
| `src/cohezion/agi/**` | @agi-research |
| `src/cohezion/learning/**` | @agi-research |
| `tests/unit/**` | @agi-research |
| `src/cohezion/compound/**` | @compound-loop |
| `src/cohezion/core/**` | @compound-loop |
| `src/cohezion/agents/**` | @compound-loop |
| `src/cohezion/universe/**` | @compound-loop |
| `tests/mycelium/**` | @compound-loop |
| `src/cohezion/data_mesh/**` | @data-mesh |
| `src/cohezion/persistence/**` | @data-mesh |
| `src/cohezion/knowledge_graph/**` | @data-mesh |
| `tests/knowledge_graph/**` | @data-mesh |

Notes:

- `tests/unit/` is owned by @agi-research with per-file exceptions (currently
  `test_delegation_logger.py`); add exceptions as rows above the baseline.
- External record-keepers are out of repo scope by design: the Obsidian vault
  (`~/vaults/cohezion-vault/`) and SurrealDB tables are shared append-only
  ledgers, not exclusive write surfaces.
- This map is a living document: when CI reports an unowned path, extend the
  map deliberately instead of adding a catch-all. A catch-all row would
  silently re-create the uncheckable boundary this map exists to prevent.