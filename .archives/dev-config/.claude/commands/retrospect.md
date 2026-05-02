Run a development retrospective that flows insights back into core files.

This is the compound engineering feedback loop. It ensures that session learnings don't just accumulate in knowledge_graph/ — they propagate back into the files that govern future behavior.

## Steps

### 1. Audit Current State
- Read `knowledge_graph/KEY_LEARNINGS.md` and `knowledge_graph/MISSION_JOURNAL.md`
- Read `CLAUDE.md`, `README.md`, and `memory/MEMORY.md`
- Read `.agent/CONSTITUTION.md`, `.agent/COHEZION_CHARTER.md`, `.agent/CAPABILITY_MAP_REDUX.md`
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
- **If it changes hard constraints**: Update `.agent/CONSTITUTION.md` (Sections 3, 8)
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

### 8. Close the Compound Loop
The retrospect is the MIDDLE feedback loop (knowledge compound). It must connect to the INNER loop (execution) and feed the OUTER loop (coordination):

- **Vault Persistence**: For each significant learning, call `vault_log_decision()` or `vault_log_experiment()` via cloud-vault-mcp tools to persist to Obsidian vault under the brain-region structure (prefrontal/decisions/, cerebellum/patterns/, hippocampus/experiments/)
- **Graph Registration**: For each code↔learning connection, use `bidirectional_linker.py` link types (DECISION_TO_CODE, PATTERN_TO_CODE, EXPERIMENT_TO_CODE) to register relationships in the knowledge graph
- **Skill Refinement**: If any learning affects a PRIME skill's effectiveness, trigger `SkillRefiner.refine()` to append the refinement to the skill definition
- **Journey Analysis**: If sufficient journey data exists, run `JourneyAnalyzer.generate_report()` on recent trajectories to detect behavioral patterns (Explorer, Stabilizer, Innovator, Oscillator, Drifter archetypes)
- **Graph Health Check**: Run `graph_health()` via cohezion-maintenance-mcp to measure connectivity coherence, orphan ratio, freshness, and link reciprocity — report Graph HIHO score

### 9. Update Continuation
If a continuation file exists for this session, update it with:
- Completed items marked
- New items from retrospective findings (graph hardening, platform coordination, protocol gaps)
- Updated competition portfolio (check for deadline extensions, priority shifts)
- Session learnings reference (L### numbers)

## Knowledge Graph Ontology (Reference)

| Node Type | SurrealDB Table | Source |
|-----------|----------------|--------|
| `neuron` | `neurons` | Vault notes (.md) |
| `decision` | `decisions` | `vault_log_decision()` |
| `experiment` | `experiments` | `vault_log_experiment()` |
| `pattern` | `patterns` | `vault_extract_pattern()` |
| `skill` | `skills` | PRIME .md files |
| `code_module` | `code_modules` | Python source files |
| `journey` | `journeys` | JourneyTracker trajectories |
| `agent` | `agents` | Agent definitions |

**Graph HIHO** = weighted avg of: connectivity (>0.8) + reciprocity (>0.6) + freshness (>0.3) + 1-orphan_ratio (<0.1). Target: 0.5 ± 0.15.

## Rules
- NEVER delete knowledge without first reading and understanding it
- Prefer compression over deletion (turn 5 verbose entries into 1 concise entry)
- Every claim in README.md must be adversarially verifiable
- CLAUDE.md is the single source of truth — other files defer to it
- Close the compound loop: every insight must flow to vault + graph + skills, not just markdown files
- Report Graph HIHO score alongside test counts
