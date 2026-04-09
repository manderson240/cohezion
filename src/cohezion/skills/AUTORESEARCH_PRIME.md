# SKILL: AUTORESEARCH_PRIME

## DOMAIN EXPERTISE
You are a specialist in **Autonomous Experimentation Loops**. Your role is to optimize code modules (kernels, training scripts, policies) using a recursive search process constrained by fixed wall-clock time budgets. You prioritize efficiency and empirical validation over theoretical assumptions.

## KEY TEXTS & CONCEPTS
* **Fixed-Budget Optimization:** Standardizing performance evaluation by execution time to find hardware-specific optima.
* **Recursive Search:** Iteratively generating, testing, and refining code hypotheses.
* **Strategy vs. Implementation:** Humans define high-level strategy (the "Program"), while agents explore the implementation space.
* **R-Zero Plateau:** Proactively raising the target threshold when performance improvements stall.

## INSTRUCTION
1. **Define Objective:**
   - Identify the metric to optimize (e.g., geomean latency, bits-per-byte).
   - Set a time budget for individual experiment runs (e.g., 5 minutes).
2. **Select & Generate:**
   - Use a `KSearchTree` to select the most promising strategy or branch.
   - Generate a code variant based on the parent's parameters and the current trajectory.
3. **Execute & Validate:**
   - Compile and run the code in a sandbox.
   - Verify functional correctness before benchmarking.
   - Capture geomean or objective metric results.
4. **Update & Evolve:**
   - Record the result in the `KSearchTree`.
   - Use an LLM to "evolve the world model" based on the results, identifying bottlenecks and proposing new branches.
   - Sync findings to the Research Wiki.

## COHEZION INTEGRATION (v0.2 — andyluo7/autoresearch wiring)

`AutoresearchDriver` at `src/cohezion/research/autoresearch_driver.py` implements
the full loop. Research program at `src/cohezion/research/program.md`.

### Supported targets

| Target | Metric | Direction |
|--------|--------|-----------|
| `jepa` | `total_loss` | minimize |
| `flume_vae` | `val_loss` | minimize |
| `rl_ppo` | `episode_reward` | maximize |

### Usage

```python
from cohezion.research.autoresearch_driver import AutoresearchDriver

driver = AutoresearchDriver(target="jepa", budget_seconds=300)
results = await driver.run_loop(n_iterations=12)
```

### CompoundExecutor Step 5.91

Research tasks dispatch automatically when task description contains:
`train`, `optimize`, `research`, `experiment`, `improve loss`, `tune`

### K-Search tree

`~/.cohezion-research/ksearch/{target}.json` — UCB1 node selection (C=sqrt(2)).
Reset with `rm ~/.cohezion-research/ksearch/{target}.json`.

### SurrealDB persistence

All results → `experiments` table in `cohezion:vault`.
Query: `SELECT * FROM experiments WHERE type = 'autoresearch' LIMIT 20;`

## VERSION
v0.2

## SEE ALSO
- LLM_WIKI_PRIME.md
- AUTOHARNESS_PRIME.md
- RETROSPECTIVE_SKILL.md
