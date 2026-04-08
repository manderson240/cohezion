# Implementation Plan: Autonomous Research & Safety Unification

## Objective
Integrate Karpathy's LLM-Wiki and Autoresearch patterns, combined with the AutoHarness safety verification framework, into the Cohezion ecosystem. This will create a closed-loop autonomous research swarm that compounds knowledge, optimizes experiments, and ensures execution reliability.

## Key Files & Context
- **Skills:** `src/cohezion/skills/*.md` (PRIME skill definitions)
- **Knowledge Graph:** `src/cohezion/knowledge_graph/wiki/` (Structured memory)
- **Swarm:** `src/cohezion/swarm/autoresearch/` (Optimization loops)
- **Compound:** `src/cohezion/compound/harness.py` (Safety verification)

## Implementation Steps

### Phase 1: Knowledge Layer (LLM-Wiki)
1.  **Create Skill:** `src/cohezion/skills/LLM_WIKI_PRIME.md` defining the "Incremental Knowledge Compilation" pattern.
2.  **Initialize Wiki:** Create `src/cohezion/knowledge_graph/wiki/` with:
    -   `index.md`: Map of all entities and concepts.
    -   `log.md`: Chronological log of ingestion and edits.
    -   `entities/`: Directory for granular concept pages.
3.  **Bootstrap Ingestion:** Create a prototype script `src/cohezion/knowledge_graph/wiki_manager.py` to ingest new research (like the AutoHarness paper) into the wiki format.

### Phase 2: Experimentation Layer (Autoresearch)
1.  **Create Skill:** `src/cohezion/skills/AUTORESEARCH_PRIME.md` defining the "Fixed-Budget Optimization Loop".
2.  **Generalize Framework:** Create `src/cohezion/swarm/autoresearch/base.py` containing a `ResearchDriver` class that abstracts the `SELECT -> GENERATE -> EVAL -> UPDATE` loop used in the Luma speedrun.
3.  **Pattern Migration:** Move common utilities (RateLimiter, KSearchTree) from the Luma-specific directory to the general `swarm/autoresearch/` package.

### Phase 3: Safety Layer (AutoHarness)
1.  **Create Skill:** `src/cohezion/skills/AUTOHARNESS_PRIME.md` defining "Automatic Synthesis of Code Harnesses".
2.  **Implement Synthesizer:** Create `src/cohezion/compound/harness.py` with a `HarnessSynthesizer` that uses an LLM to generate test harnesses for agent-proposed code.
3.  **Executor Integration:** Update `CompoundExecutor` (or equivalent) to invoke the harness before applying critical code changes.

## Verification & Testing
- **Wiki Verification:** Confirm `wiki_manager.py` correctly populates `entities/` from a raw markdown source.
- **Autoresearch Verification:** Run a dummy optimization loop (e.g., optimizing a simple math function) using the generalized `ResearchDriver`.
- **Harness Verification:** Verify that the `HarnessSynthesizer` can detect a trivial OOM or SyntaxError in a proposed "optimization" script.

## Success Metrics
- **Knowledge Compounding:** 100% of new research papers ingested into structured Wiki entities.
- **Autonomous ROI:** 10-15% improvement in geomean performance metrics via autonomous loops.
- **Zero-Failure Execution:** 100% detection of invalid agent-proposed code changes via AutoHarness before execution.
