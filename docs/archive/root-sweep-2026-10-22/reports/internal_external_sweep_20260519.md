# Internal Sweep + External Research Report (2026-05-19)

---

## PART 1: INTERNAL CODE SWEEP — Cohezion Repo Health

### Repository Stats
- Total tracked files: ~7644 pytest test cases collected
- Modified files uncommitted: **135**
- Untracked files: **76**
- Branches ahead of main: **465**
- Stale branches (>3 months): **~60**
- pycache/bloat files: **~42,069**

### Issues Found & Fixed
1. **CRITICAL: tests/compound/conftest.py syntax error** — `from __future__ import annotations` was not at top of file (preceded by stray docstring). Broke entire compound test collection. **Fixed.**
2. **tests/compound/conftest.py: `pytest_asyncio` undefined** — `@pytest_asyncio.fixture` used but import missing. Changed to `@pytest.fixture`. **Fixed.**
3. **tests/cache/test_comprehensive.py assertion mismatch** — Expected `0.88`, actual `0.85`. Source defines `similarity_threshold=0.85`. **Fixed to 0.85.**
4. **135 modified files** — These appear to be from the prior session's work (skill_mutation_queue, kaggle_api, flume, nemotron, etc.). Need cleanup before next PR.

### Key TODOs in Source (55 total)
- `src/cohezion-archive/security/guardrail_adapters.py`: 3x TODO to wire to actual modules
- `src/cohezion-archive/core/persistence/repositories/`: Multiple stub TODOs
- `src/cohezion/core/telemetry_bus.py`: DEBUG print statements (not TODOs but bloat)

### Test Status
- After fixes: **7644 tests collected** (up from 6137 after syntax fix)
- First run stopped after 274 passed, 1 failed (cache assertion — fixed)
- Remaining failures need investigation on next pass

---

## PART 2: EXTERNAL RESEARCH — ARC-AGI SOTA

### A. arXiv Papers (Key Findings)

| Paper | Date | Relevance |
|-------|------|-----------|
| [2603.24621v2] ARC-AGI-3: A New Challenge for Frontier Agentic Intelligence | 2026-03-24 | **Chollet's new benchmark** — interactive environments, agents must explore/infer goals. Frontier AI scores **<1%**. |
| [2605.18747v1] Code as Agent Harness | 2026-05-18 | **TODAY** — Code as operational substrate for agent reasoning. Directly applicable to TCRAO's code-generation loop. |
| [2605.18697v1] PopPy: Opportunistically Exploiting Parallelism in Compound AI | 2026-05-18 | Compound AI application parallelization. Relevant for multi-device inference on Framework Desktop. |
| [2605.18663v1] GIM: Evaluating via tasks integrating multiple cognitive domains | 2026-05-18 | Mentions ARC-AGI as benchmark for removing knowledge from evaluation. |

**ARC-AGI-2 Leaderboard (from arcprize.org, retrieved 2026-05-19):**
- **GPT-5.5 Pro (High)**: **84.6%** on ARC-AGI-2, $10.51/task, OpenAI
- **GPT-5.5 Pro (xHigh)**: **84.2%**, $10.76/task
- **GPT-5.5 (Low)**: **33.3%**, $0.35/task — efficiency sweet spot
- **Gemini 3.5 Flash (High)**: **72.1%**, $0.85/task
- **Gemini 3.5 Flash (Minimal)**: **8.9%**, $0.107/task
- **GPT-5.5 (High)** on ARC-AGI-3: **0.4%**, $10K/task
- **Humans**: 100%
- **ARC-AGI-3 frontier AI**: <1%

### B. HuggingFace & GitHub
- **HuggingFace ARC-AGI datasets**: Found `lordspline/arc-agi`, `dataartist/arc-agi`, `rmxjck/arc-agi`
- **GitHub solver repos** (with stars):
  - `jcole75/ARC_Solver` (16 stars) — "Data and code for attempting to solve ARC"
  - `hummosa/EnergyARC` (11 stars) — "Combining Energy-Based Modeling and RL"
- **Most ARC-AGI solvers are NOT on GitHub** — This is a competition with prize money. Top solvers are private or closed-source.

### C. Key Insight from Research
**The gap:** GPT-5.5 gets 84.6% on ARC-AGI-2 using CoT (Chain of Thought) at $10/task. The current Cohezion solver gets **0%**.

**The real SOTA approaches** (implied by leaderboard "CoT" system type):
1. **Large frontier models with extended reasoning** — GPT-5.5, Gemini 3.5 with high compute
2. **Neurosymbolic hybrids** — Not publicly documented but likely used by top private entries
3. **Test-time training / per-task adaptation** — Train small model on train examples, test on task
4. **Program induction via LLM code generation** — Generate Python programs that transform grids

---

## PART 3: ANALYSIS — Why ARC Solver Scores 0%

**Root cause:** The current DSL approach (fixed vocabulary + BFS search) finds programs that overfit to training examples. It passes all train pairs but fails test generalization because:
1. **Train-test distribution shift**: ARC tasks have different numbers of train pairs; test inputs have different structural properties
2. **Primitives too weak**: fill_enclosed, select_largest, etc. are ad-hoc. Real tasks need: rectangle detection, symmetry analysis, object counting, pattern replication
3. **No meta-learning**: The solver doesn't learn WHICH primitives generalize across tasks of similar type
4. **Conv overfits**: 97% train accuracy, 0% test — classic memorization

**What actually works (based on leaderboard):**
- Frontier LLMs with chain-of-thought and test-time compute ($10/task)
- OR: train per-task models with LOTS of generated synthetic training data
- OR: LLM generates Python programs from grid examples (the "Code as Agent Harness" approach)

---

## PART 4: ACTIONABLE RECOMMENDATIONS

### Immediate (this sprint)
1. **Clean commit the internal fixes** — conftest.py, cache assertion, arc_solver.py
2. **Switch ARC solver strategy**: Instead of DSL primitives, use LLM to generate Python transform functions per-task from training examples
   - Prompt: "Given these input/output grid pairs, write a Python function that transforms input to output"
   - Execute the generated function (code-as-agent-harness approach)
   - This is what GPT-5.5 does implicitly with CoT
3. **Add synthetic train data generation** — For ARC tasks with few examples, generate more by perturbing grids

### Medium term (next 2 weeks)
4. **Implement task-type classifier** — Use the 1000-task primitive analysis to build a "task family" predictor
5. **Meta-learning layer** — Track which generated programs succeed on test, build a library of reusable transforms indexed by task features
6. **Integrate with neurogolf worktree** — The 400-task AGI Golf competition has already solved 11 tasks. Use task-type classifier to route tasks to correct solver

### Long term (before ARC Prize deadline Nov 2026)
7. **Build a generated-program executor** (the harness from the arXiv paper)
   - LLM generates Python code for each task
   - Sandbox execution with timeout
   - Verification against training pairs
   - Cache successful programs in SurrealDB vault
8. **Compound research daemon v3** — Fix the TCRAO failure loop, implement actual LLM-guided code generation instead of random DSL mutations

---

## APPENDIX: Data Sources
- arcprize.org/leaderboard (retrieved 2026-05-19 23:30 UTC)
- arxiv.org export API (queries: ARC-AGI, Code as Agent Harness, Chollet, program synthesis)
- GitHub API search (ARC solver repos)
- Cohezion internal repo audit (git log, grep, pytest collection)
