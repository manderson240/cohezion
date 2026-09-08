# Developer Tutorial & Walkthrough: Tripartite Goal Loop Architecture & Trace-to-Goal Refactor

**Author:** Cohezion Core Engineering Team  
**Audience:** Systems Engineers, Autonomous Agent Developers, and Distributed ML Architects  
**Prerequisites:** Familiarity with Discrete Cellular Sheaves, Hyperbolic Geometry (Poincaré Ball), SurrealDB v2, and Marimo Reactive Notebooks.

---

## 1. Architectural Motivation: Why Linear Execution Traces Were Refactored

Historically, autonomous agent runtimes rely on **linear, append-only event logging** (such as logging rows into `event_log` or `JOURNEY_STEP` streams). While this passive logging captures history, it suffers from three fundamental design failure modes:

1. **The Silent Loss Trap (Open-Loop Execution):**  
   Linear traces record failures (e.g., `SECURITY_VIOLATION`, `SYSTEM_HEALTH` alarms, AST compilation errors) but lack any intrinsic corrective feedback loop. Work continues blindly or halts without state recovery.
2. **Missing Invariant Verification:**  
   Passive logging cannot test whether the agent's actions preserve architectural invariants (such as producer-consumer wiring, memory thresholds, or dormancy constraints).
3. **No Retrospective Reinforcement:**  
   Past failures are buried in unstructured logs rather than compiled into reusable experiential memory or zero-knowledge mathematical proofs.

### The Paradigm Shift: Closed Feedback Control

To solve this, Cohezion refactored passive linear traces into **active, closed-loop goal state machines**:

$$\text{Passive Linear Trace} \longrightarrow \text{Active Feedback Control Loop}$$

```
                ┌──────────────────────────────────────────────┐
                │             Tripartite Goal Loop             │
                │                                              │
  Goal Spec ───►│  [Phase 1] Internal Codebase Sweep           │
                │       │                                      │
                │  [Phase 2] Bleeding Edge Research & LLM      │
                │       │                                      │
                │  [Phase 3] Experiential Learning & ZK-FV     │
                └───────┬──────────────────────────────▲───────┘
                        │                              │
                        ▼                              │
             Candidate Strategy Step                   │
                        │                              │
                  Check Invariant ─────────────────────┘
                 (Satisfied? No -> Refine)
                        │
                        ▼ (Satisfied? Yes)
           Dual Persistence (Vault + SurrealDB)
```

In this architecture:
- Every task is formalized as a durable, disk-backed **`GoalSpecification`** (`goal_id`, `target_metric`, `target_threshold`).
- Each iteration executes three mutually enforcing phases: **Sweep**, **Research**, and **Learning**.
- Execution minimizes the Sheaf Dirichlet Energy:
  $$E_D(x) = \frac{1}{2} x^\top L_\mathcal{F} x$$
  driving disparate subagent representations into harmonic consensus.

---

## 2. Deep Dive: The Three Tripartite Phases

### Phase 1: Internal Codebase Sweep
Before taking any external or expensive LLM action, the system performs an internal structural audit:
- **Producer-Consumer Invariant:** Scans for disconnected endpoints or hollow mock seams (`producer_consumer_audit.py`).
- **Dormancy Scan:** Ensures load-bearing skills and capabilities remain active (`dormancy_scan.py`).
- **AgY Settings Check:** Confirms `runningLightSpeed` is configured to `fast`.
- **Integrity Score ($I \in [0.0, 1.0]$):** If $I < 0.85$, execution immediately refines internal wiring before consulting external models.

### Phase 2: Bleeding Edge Research
When a failure or drift is encountered, the agent grounds its strategy selection in frontier computer science literature:
- **AutoHarness (arXiv:2603.03329v1):** Deterministic Code-as-Action verifiers that bypass slow LLM generation with 0ms AST-level guardrails.
- **Graphiti (arXiv:2501.13956):** Bi-temporal knowledge graph memory for temporal invalidation of outdated skills.
- **A-MEM (arXiv:2501.13783):** Dynamic synaptic evolution using Hebbian plasticity and retroactive reinforcement.
- **Cellular Sheaves (arXiv:2412.08832):** Discrete Laplacian harmonic analysis for multi-agent consensus.

On hardware equipped with local silicon (e.g. AMD Strix Halo APU with 128GB Unified Memory), Tier 1 models (such as `Bonsai-8B-gguf` or `Qwen-2.5-Coder-7B`) run locally on Lemonade port `13305`, eliminating external API latency and cloud reliance.

### Phase 3: Experiential Learning & Formal Verification
Following strategy execution:
1. **AutoHarness AST Gate:** Evaluates system bytecode/memory constraints in 0ms.
2. **Zero-Knowledge Formal Verification (ZK-FV):** Compiles AST constraints into Plonkish gates (`GATE_BOUNDS_CHECK`, `GATE_HARMONIC_CONSENSUS`) and generates an in-process cryptographic proof `zkproof-...`.
3. **Reward Assignment ($r_t$):** Formulates an empirical reward scalar based on step success, AST safety, and ZK proof validity.
4. **Dual Persistence Engine:**
   - **Obsidian Vault (`~/vaults/cohezion-vault/01-Learnings/`):** Human-readable Markdown notes with YAML frontmatter, citations, and retrospective distillations.
   - **SurrealDB v2 (`experiential_replay`, `goal`):** Bi-temporal graph nodes and records for immediate semantic recall.

---

## 3. Code Walkthrough

### 3.1 `GoalDrivenTraceLoop` (`src/cohezion/recursive_trace/goal_loop.py`)
Encapsulates monadic error containment and failure-conditioned strategy progression:

```python
from cohezion.recursive_trace.goal_loop import GoalDrivenTraceLoop, GoalTraceTask

loop = GoalDrivenTraceLoop(
    strategies=[
        "cellular_sheaf_diffusion",
        "autoharness_bytecode_verification",
        "poincare_conformal_reprojection",
    ],
    failure_map={
        "initial": ["cellular_sheaf_diffusion"],
        "drift": ["poincare_conformal_reprojection"],
        "syntax_error": ["autoharness_bytecode_verification"],
    },
    max_depth=4,
)

task = GoalTraceTask(
    goal_id="task_harmonic_sync",
    condition="Dirichlet Energy E_D <= 0.10",
    initial_failure_class="initial",
)


def step_executor(task, strategy):
    # Monadic, fail-safe execution
    return True, f"Successfully executed {strategy}", None


result = loop.run(task, step_executor)
assert result.solved is True
```

### 3.2 `TripartiteGoalLoop` (`src/cohezion/recursive_trace/tripartite_goal_loop.py`)
Coordinates the internal sweep, frontier research, and experiential learning:

```python
from cohezion.flume.loop_goal_refactor_engine import GoalSpecification
from cohezion.recursive_trace.tripartite_goal_loop import TripartiteGoalLoop

goal = GoalSpecification(
    goal_id="stabilize_strix_halo_mesh",
    title="Stabilize AMD Strix Halo APU Mesh & UMA Latency",
    target_metric="coherence",
    target_threshold=0.90,
    max_iterations=3,
)

tri_loop = TripartiteGoalLoop(max_depth=3)
res = tri_loop.run(goal)

print(
    f"Goal: {res.goal.title} | Converged: {res.converged} | Reward:"
    f" {res.final_reward:.2f}"
)
for note in res.vault_notes_created:
    print(f"  Emitted Vault Note: {note}")
```

### 3.3 `refactor_traces_to_goals.py` (`scripts/ops/refactor_traces_to_goals.py`)
Scans recent `event_log` traces from SurrealDB, transforms actionable signals into `GoalSpecification`s, and runs closed loops:

```bash
# Dry-run inspection
python scripts/ops/refactor_traces_to_goals.py --limit 30 --dry-run

# Persist synthesized goals into SurrealDB
python scripts/ops/refactor_traces_to_goals.py --limit 30 --execute

# Execute autonomous goal loops and persist loop results
python scripts/ops/refactor_traces_to_goals.py --limit 30 --execute --run-loop
```

---

## 4. Interactive Marimo Reactive Notebook: Local & WASM

The interactive visualizer is located at:
`notebooks/marimo/tripartite_goal_loop_explorer.py`

### Running Locally with Python
To run the notebook as a headless or script check:
```bash
python notebooks/marimo/tripartite_goal_loop_explorer.py
```

### Running Locally with the Interactive Marimo Server
To launch the interactive GUI with live sliders and 3D Plotly plots:
```bash
# In edit mode (interactive notebook developer interface)
marimo edit notebooks/marimo/tripartite_goal_loop_explorer.py

# In app/dashboard mode (clean full-page interactive application)
marimo run notebooks/marimo/tripartite_goal_loop_explorer.py
```

### Exporting and Running in Browser via WASM (Zero-Server Deployment)
The notebook is built to be 100% WASM-compatible with Pyodide:
```bash
marimo export html-wasm notebooks/marimo/tripartite_goal_loop_explorer.py -o dist/tripartite_goal_loop_explorer.html
```
Once exported, open `dist/tripartite_goal_loop_explorer.html` in any modern web browser or serve via static hosting (e.g. GitHub Pages or an S3 bucket). The reactive sliders, Dirichlet decay calculations, and 3D Poincaré ball Plotly renders will execute purely inside client-side WebAssembly!

---

## 5. Verification & Code Quality Standards

Both files strictly adhere to project coding guidelines:
- Fully type-annotated (`from __future__ import annotations`).
- Verified for formatting and linting via Ruff:
  ```bash
  ruff check notebooks/marimo/tripartite_goal_loop_explorer.py
  ruff format notebooks/marimo/tripartite_goal_loop_explorer.py
  ```
- Fast in-process unit tests can be validated with:
  ```bash
  pytest tests/unit/test_tripartite_goal_loop.py -v
  ```
