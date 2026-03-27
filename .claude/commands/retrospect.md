Run a development retrospective that flows insights back into core files.

This is the compound engineering feedback loop. It ensures that session learnings don't just accumulate in knowledge_graph/ — they propagate back into the files that govern future behavior.

## Steps

### 1. Audit Current State
- Read `knowledge_graph/KEY_LEARNINGS.md` and `knowledge_graph/MISSION_JOURNAL.md`
- Read `CLAUDE.md`, `README.md`, and `memory/MEMORY.md`
- Identify: new learnings since last retrospect, stale/duplicate entries, insights that should propagate upward

### 2. Prune Knowledge Graph
- Remove duplicate entries from KEY_LEARNINGS.md (e.g., triplicate retrospective blocks)
- Remove spam entries from MISSION_JOURNAL.md (e.g., repeated "Automated Hypothesis Testing Report" lines)
- Compress old session developments into single-line summaries
- Target: KEY_LEARNINGS.md under 300 lines, MISSION_JOURNAL.md under 150 lines

### 3. Propagate Insights Upward
For each significant learning or pattern discovered since last retrospect:
- **If it changes how we code**: Update `CLAUDE.md` Coding Standards or Operational Protocols
- **If it changes what the project can do**: Update `README.md` Verified Capabilities or Limitations
- **If it changes architecture**: Update `.agent/CAPABILITY_MAP.md`
- **If it changes theory**: Update `.agent/COHEZION_CHARTER.md`
- **If it's a process lesson**: Update `memory/MEMORY.md` (keep under 200 lines)

### 4. Persist to SurrealDB + Obsidian Vault
- Write key learnings to SurrealDB `prompt_artifacts` table via `genesis_persistence.persist_prompt_artifact()`
  - Each learning becomes a prompt artifact with `model_id="retrospective"` for queryability
- Write universe snapshot to SurrealDB: current test count, module count, coherence metrics
  - Use `genesis_persistence.persist_universe_snapshot()` with tick = session number
- Check Obsidian Vault (`~/vaults/cohezion-vault/`) for relevant entries:
  - Sync new learnings that belong in vault categories (decisions/, patterns/, experiments/)
  - Cross-reference vault decisions with KEY_LEARNINGS to avoid duplication
- Verify SurrealDB genesis tables are populated: `SELECT count() FROM journey_transitions GROUP ALL;`

### 5. Update Genesis Engine Metrics
- Run `uv run pytest tests/physics/ tests/world_model/ tests/environments/ tests/swarm/test_topological_router.py -q -o addopts=""`
- Count genesis-specific modules: `find src/cohezion/physics/ src/cohezion/world_model/ src/cohezion/environments/ -name '*.py' | wc -l`
- Count frontend components: `find src/web/anima_dashboard/src/components/genesis/ -name '*.tsx' | wc -l`
- Count API endpoints: verify genesis + world-model router route counts
- Update CLAUDE.md with accurate genesis metrics
- Update `.agent/CAPABILITY_MAP_REDUX.md` if new capabilities added

### 6. Verify Consistency
- Ensure CLAUDE.md reflects the actual codebase state (module count, test coverage, etc.)
- Ensure README.md has no fabricated claims
- Ensure memory/MEMORY.md is under the 200-line limit
- Run `ruff check src/cohezion/` to verify no regressions

### 7. Report
- List what was pruned, what was propagated, and what remains stale
- Note any inconsistencies between core files that need manual resolution
- Report SurrealDB row counts for genesis tables

## Rules
- NEVER delete knowledge without first reading and understanding it
- Prefer compression over deletion (turn 5 verbose entries into 1 concise entry)
- Every claim in README.md must be adversarially verifiable
- CLAUDE.md is the single source of truth — other files defer to it
