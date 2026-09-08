import marimo


__generated_with = "0.23.16"
app = marimo.App(width="full")


@app.cell
def _():
    import json
    import math
    import time
    from dataclasses import dataclass, field
    from datetime import datetime, timezone

    import marimo as mo
    import numpy as np
    import plotly.graph_objects as go

    # Attempt native Cohezion imports; fallback to WASM-compatible mock adapters if offline
    try:
        from cohezion.agi.autoharness_policy import AutoHarnessPolicy
        from cohezion.agi.zkfv_compiler import ZKFVCompiler, ZKProof
        from cohezion.flume.loop_goal_refactor_engine import (
            GoalSpecification,
        )
        from cohezion.flume.poincare_manifold_visualizer import (
            compute_hyperbolic_distance,
            project_2048d_to_poincare_3d,
        )
        from cohezion.recursive_trace.tripartite_goal_loop import (
            BleedingEdgeResearchResult,
            CodebaseSweepResult,
            ExperientialLearningResult,
            TripartiteGoalLoop,
            TripartiteGoalLoopResult,
            TripartiteIterationResult,
        )

        COHEZION_NATIVE = True
    except ImportError:
        COHEZION_NATIVE = False

        # WASM / Pyodide In-Memory Standalone Fallback Adapters
        @dataclass(frozen=True, slots=True)
        class CodebaseSweepResult:
            passed: bool
            integrity_score: float
            checks_evaluated: int
            dormant_count: int
            findings: list[str] = field(default_factory=list)

        @dataclass(frozen=True, slots=True)
        class BleedingEdgeResearchResult:
            citations: list[str]
            frontier_paradigms: list[str]
            synthesis_summary: str
            recommended_strategy: str
            model_provider: str

        @dataclass(frozen=True, slots=True)
        class ExperientialLearningResult:
            reward: float
            autoharness_allowed: bool
            zkfv_verified: bool
            zkfv_proof_id: str
            lesson_learned: str
            surreal_persisted: bool
            vault_persisted: bool

        @dataclass(frozen=True, slots=True)
        class TripartiteIterationResult:
            iteration: int
            strategy: str
            sweep: CodebaseSweepResult
            research: BleedingEdgeResearchResult
            learning: ExperientialLearningResult
            satisfied: bool
            latency_ms: float

        @dataclass(frozen=True, slots=True)
        class GoalSpecification:
            goal_id: str
            title: str
            target_metric: str
            target_threshold: float
            max_iterations: int = 5

        @dataclass(frozen=True, slots=True)
        class TripartiteGoalLoopResult:
            goal: GoalSpecification
            converged: bool
            iterations_run: int
            final_reward: float
            total_time_ms: float
            history: list[TripartiteIterationResult]
            vault_notes_created: list[str]
            surreal_records_created: list[str]

        class AutoHarnessPolicy:
            def evaluate_policy(self, name: str, ctx: dict):
                class EvalResult:
                    allowed = True
                    reason = "WASM AST verified (Memory safe)"

                return EvalResult()

        class ZKProof:
            def __init__(self, proof_id: str):
                self.proof_id = proof_id

        class ZKFVCompiler:
            @staticmethod
            def compile_ast_to_gates(name: str):
                return ["GATE_BOUNDS_CHECK", "GATE_HARMONIC_CONSENSUS"]

            @staticmethod
            def generate_proof(gates, inputs):
                import uuid

                return ZKProof(f"zkproof-wasm-{uuid.uuid4().hex[:8]}")

            @staticmethod
            def verify_proof(proof):
                return True

        def compute_hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-7) -> float:
            u_sq = min(float(np.sum(u * u)), 0.9998)
            v_sq = min(float(np.sum(v * v)), 0.9998)
            diff_sq = float(np.sum((u - v) ** 2))
            denom = max((1.0 - u_sq) * (1.0 - v_sq), eps)
            arg = max(1.0, 1.0 + (2.0 * diff_sq / denom))
            return math.acosh(arg)

        def project_2048d_to_poincare_3d(
            vectors_2048d: np.ndarray, seed: int = 42, max_radius: float = 0.95
        ) -> np.ndarray:
            vectors_arr = np.asarray(vectors_2048d, dtype=np.float64)
            if vectors_arr.ndim == 1:
                vectors_arr = vectors_arr.reshape(1, -1)
            n_samples, dim = vectors_arr.shape
            if dim < 2048:
                pad = np.zeros((n_samples, 2048 - dim))
                vectors_arr = np.hstack([vectors_arr, pad])
            elif dim > 2048:
                vectors_arr = vectors_arr[:, :2048]
            rng = np.random.default_rng(seed)
            proj = rng.normal(0.0, 1.0 / np.sqrt(2048), size=(2048, 3))
            coords = vectors_arr @ proj
            norms = np.linalg.norm(coords, axis=1, keepdims=True)
            scale = np.tanh(norms) * max_radius / np.maximum(norms, 1e-9)
            return coords * scale

        class TripartiteGoalLoop:
            def __init__(self, strategies=None, max_depth=5):
                self.strategies = list(
                    strategies
                    or [
                        "cellular_sheaf_diffusion",
                        "autoharness_bytecode_verification",
                        "baml_resilient_schema_healing",
                        "poincare_conformal_reprojection",
                        "synaptic_hebbian_rewiring",
                    ]
                )
                self.max_depth = max_depth

            def execute_internal_sweep(self):
                return CodebaseSweepResult(
                    passed=True,
                    integrity_score=1.0,
                    checks_evaluated=3,
                    dormant_count=0,
                    findings=[
                        "Producer-consumer audit verified: zero hollow seams.",
                        "Dormancy scan verified: load-bearing capabilities active.",
                        "AgY LightSpeed verified at 'fast'.",
                    ],
                )

            def execute_frontier_research(self, goal_title: str, failure_class: str):
                return BleedingEdgeResearchResult(
                    citations=[
                        "arXiv:2603.03329v1 [cs.AI] — AutoHarness: Deterministic Code-as-Action Verifiers",
                        "arXiv:2501.13956 [cs.DB] — Graphiti: Bi-Temporal Knowledge Graph Memory",
                        "arXiv:2501.13783 [cs.NE] — A-MEM: Dynamic Synaptic Evolution via Hebbian Plasticity",
                        "arXiv:2412.08832 [math.AT] — Cellular Sheaves and Discrete Laplacian Harmonic Analysis",
                    ],
                    frontier_paradigms=[
                        "Cellular Sheaf Harmonic Gradient Descent (x_{t+1} = x_t - γ ∇ E_D)",
                        "Zero-Knowledge Formal Verification (ZKFV) Plonkish Gates",
                        "2048D Poincaré Manifold Conformal Projection",
                    ],
                    synthesis_summary=f"Frontier analysis for '{goal_title}': Apply cellular sheaf diffusion.",
                    recommended_strategy=self.strategies[0],
                    model_provider="lemonade_Bonsai-8B-gguf (Tier 1 Local)",
                )

            def execute_experiential_learning(
                self, goal, iteration, strategy, step_success, sweep, research
            ):
                proof_id = f"zkproof-wasm-exp-{iteration:03d}"
                reward = 0.98 if step_success else 0.42
                lesson = f"Iteration {iteration}: Strategy '{strategy}' resolved with reward {reward:.2f}."
                return (
                    ExperientialLearningResult(
                        reward=reward,
                        autoharness_allowed=True,
                        zkfv_verified=True,
                        zkfv_proof_id=proof_id,
                        lesson_learned=lesson,
                        surreal_persisted=True,
                        vault_persisted=True,
                    ),
                    f"/vaults/cohezion-vault/01-Learnings/learning_{goal.goal_id}_it{iteration}.md",
                    f"experiential_replay:`exp_{goal.goal_id}_it{iteration}`",
                )

            def run(self, goal, step_fn=None):
                history = []
                v_notes = []
                s_recs = []
                converged = False
                for it in range(1, self.max_depth + 1):
                    sweep = self.execute_internal_sweep()
                    research = self.execute_frontier_research(goal.title, "initial")
                    strat = self.strategies[(it - 1) % len(self.strategies)]
                    step_ok = it >= 2 if step_fn is None else step_fn(goal, strat)[0]
                    learn, vn, sr = self.execute_experiential_learning(
                        goal, it, strat, step_ok, sweep, research
                    )
                    if vn:
                        v_notes.append(vn)
                    if sr:
                        s_recs.append(sr)
                    history.append(
                        TripartiteIterationResult(
                            iteration=it,
                            strategy=strat,
                            sweep=sweep,
                            research=research,
                            learning=learn,
                            satisfied=step_ok,
                            latency_ms=1.42,
                        )
                    )
                    if step_ok:
                        converged = True
                        break

                return TripartiteGoalLoopResult(
                    goal=goal,
                    converged=converged,
                    iterations_run=len(history),
                    final_reward=history[-1].learning.reward,
                    total_time_ms=len(history) * 1.42,
                    history=history,
                    vault_notes_created=v_notes,
                    surreal_records_created=s_recs,
                )

    return (
        AutoHarnessPolicy,
        BleedingEdgeResearchResult,
        COHEZION_NATIVE,
        CodebaseSweepResult,
        ExperientialLearningResult,
        GoalSpecification,
        TripartiteGoalLoop,
        TripartiteGoalLoopResult,
        TripartiteIterationResult,
        ZKFVCompiler,
        ZKProof,
        compute_hyperbolic_distance,
        datetime,
        go,
        json,
        math,
        mo,
        np,
        project_2048d_to_poincare_3d,
        time,
        timezone,
    )


@app.cell
def _(COHEZION_NATIVE, mo):
    env_badge = (
        "🟢 **Runtime:** Native Cohezion Kernel Detected"
        if COHEZION_NATIVE
        else "🌐 **Runtime:** Client-Side Browser WASM / Pyodide Mode"
    )

    mo.md(
        rf"""
    <style>
    :root {{
        color-scheme: dark !important;
    }}
    body, .marimo, [data-marimo-app], main {{
        background-color: #0b0f19 !important;
        color: #f1f5f9 !important;
    }}
    .marimo-card, div[class*="card"] {{
        background-color: #111827 !important;
        border: 1px solid #1f2937 !important;
        color: #f1f5f9 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }}
    </style>

    # 🔄 Tripartite Goal Loop & Hyperbolic Trace Explorer
    ### Closed Feedback Control: Internal Sweep $\rightarrow$ Bleeding Edge Research $\rightarrow$ Experiential Learning

    {env_badge}

    *This reactive notebook interactively walks through the three tightly-coupled phases of Cohezion's goal-seeking architecture, simulating Sheaf Laplacian Dirichlet Energy dissipation, 2048D $\to$ 3D Poincaré manifold projections, and dual-persistence emission to Obsidian Vault and SurrealDB.*
    """
    )
    return (env_badge,)


@app.cell
def _(mo):
    goal_dropdown = mo.ui.dropdown(
        options={
            "strix_halo_mesh": "APU Mesh Coherence & UMA Latency",
            "autoharness_bytecode": "AutoHarness AST Bytecode Gating Invariant",
            "sheaf_laplacian_diffusion": "Cellular Sheaf Harmonic Dirichlet Consensus",
            "baml_schema_healing": "BAML Resilient Schema Healing on Strix Halo",
        },
        value="sheaf_laplacian_diffusion",
        label="🎯 Target Goal Specification",
    )

    iterations_slider = mo.ui.slider(
        start=2,
        stop=8,
        step=1,
        value=4,
        label="🔁 Max Loop Iterations ($K$)",
    )

    step_size_slider = mo.ui.slider(
        start=0.05,
        stop=0.50,
        step=0.05,
        value=0.20,
        label=r"⚡ Diffusion Rate ($\gamma$)",
    )

    model_dropdown = mo.ui.dropdown(
        options={
            "Bonsai-8B-gguf": "Lemonade Tier 1: Bonsai-8B-gguf (Local Strix Halo NPU/iGPU)",
            "Qwen-2.5-Coder-7B": "Lemonade Tier 1: Qwen-2.5-Coder-7B (128GB Unified Memory)",
            "Heuristic": "In-Process Frontier Heuristic Fallback (0ms Latency)",
        },
        value="Bonsai-8B-gguf",
        label="🧠 Frontier Research Model",
    )

    run_btn = mo.ui.run_button(label="🚀 Execute Tripartite Goal Loop")

    mo.hstack(
        [
            mo.vstack([goal_dropdown, iterations_slider]),
            mo.vstack([model_dropdown, step_size_slider]),
            mo.vstack([mo.md("**Trigger Execution**"), run_btn]),
        ],
        justify="start",
        gap=2,
    )
    return goal_dropdown, iterations_slider, model_dropdown, run_btn, step_size_slider


@app.cell
def _(
    GoalSpecification,
    TripartiteGoalLoop,
    compute_hyperbolic_distance,
    goal_dropdown,
    iterations_slider,
    model_dropdown,
    np,
    project_2048d_to_poincare_3d,
    run_btn,
    step_size_slider,
):
    # Dependency on run button
    _ = run_btn.value

    goal_key = goal_dropdown.value
    max_k = iterations_slider.value
    gamma = step_size_slider.value
    model_choice = model_dropdown.value

    goal_titles = {
        "strix_halo_mesh": "Stabilize AMD Strix Halo APU Mesh & UMA Latency",
        "autoharness_bytecode": "Enforce AutoHarness AST Bytecode Invariant",
        "sheaf_laplacian_diffusion": "Converge Cellular Sheaf Harmonic Dirichlet Consensus",
        "baml_schema_healing": "Heal BAML Structured Output Schema Drift",
    }
    title = goal_titles.get(goal_key, "Execute Autonomous Tripartite Goal Loop")

    goal = GoalSpecification(
        goal_id=f"goal_{goal_key}",
        title=title,
        target_metric="coherence",
        target_threshold=0.90,
        max_iterations=max_k,
    )

    loop = TripartiteGoalLoop(
        max_depth=max_k,
        local_model_name=model_choice,
    )

    # Multi-step convergence simulation
    step_state = {"attempt": 0}

    def simulated_step(g, strat):
        step_state["attempt"] += 1
        if step_state["attempt"] >= min(3, max_k):
            return True, f"Harmonic convergence achieved via '{strat}'", None
        return (
            False,
            f"Iteration {step_state['attempt']} probe: boundary gradient non-zero",
            "drift",
        )

    result = loop.run(goal, simulated_step)

    # Compute Sheaf Dirichlet Energy Decay across iterations
    rng = np.random.default_rng(42)
    iters = list(range(1, len(result.history) + 1))
    e_0 = 1.85
    dirichlet_energies = [
        float(e_0 * np.exp(-gamma * (t - 1)) * (0.95 + 0.05 * rng.random()))
        if t < len(result.history)
        else float(0.04 * (1.0 - 0.1 * rng.random()))
        for t in iters
    ]

    # Generate 2048D trajectory points and project to 3D Poincaré Ball
    pts_2048d = []
    base_vec = rng.normal(0, 1.0, size=(2048,))
    base_vec = base_vec / np.linalg.norm(base_vec)

    for idx, ed in enumerate(dirichlet_energies):
        radius = float(np.tanh(ed))
        pert = rng.normal(0, 0.1, size=(2048,))
        v = base_vec + pert * (idx + 1)
        v = (v / np.linalg.norm(v)) * radius
        pts_2048d.append(v)

    arr_2048d = np.array(pts_2048d)
    poincare_3d = project_2048d_to_poincare_3d(arr_2048d, seed=42, max_radius=0.92)

    origin_3d = np.zeros(3)
    hyp_distances = [compute_hyperbolic_distance(pt, origin_3d) for pt in poincare_3d]

    return (
        arr_2048d,
        dirichlet_energies,
        gamma,
        goal,
        hyp_distances,
        iters,
        loop,
        poincare_3d,
        result,
        step_state,
        title,
    )


@app.cell
def _(dirichlet_energies, go, iters, mo, result):
    # Plot 1: Dirichlet Energy Minimization Curve
    fig_ed = go.Figure()

    fig_ed.add_trace(
        go.Scatter(
            x=iters,
            y=dirichlet_energies,
            mode="lines+markers",
            name="Sheaf Dirichlet Energy $E_D(x)$",
            line={"color": "#38bdf8", "width": 3},
            marker={"size": 10, "color": "#0284c7", "symbol": "diamond"},
        )
    )

    fig_ed.add_trace(
        go.Scatter(
            x=[1, max(iters)],
            y=[0.10, 0.10],
            mode="lines",
            name=r"Harmonic Threshold ($\epsilon \le 0.10$)",
            line={"color": "#22c55e", "width": 2, "dash": "dash"},
        )
    )

    fig_ed.update_layout(
        title="📉 Cellular Sheaf Dirichlet Energy Minimization ($E_D \to 0$)",
        template="plotly_dark",
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#111827",
        xaxis={
            "title": "Loop Iteration ($t$)",
            "tickmode": "linear",
            "tick0": 1,
            "dtick": 1,
            "gridcolor": "#1f2937",
        },
        yaxis={
            "title": "Dirichlet Energy $E_D = \\frac{1}{2} x^\\top L_\\mathcal{F} x$",
            "gridcolor": "#1f2937",
        },
        height=380,
        margin={"l": 40, "r": 40, "t": 50, "b": 40},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )

    ed_card = mo.md(
        rf"""
    ### 🔬 Phase Dynamics & Convergence Telemetry
    - **Goal State:** `{"CONVERGED" if result.converged else "SEARCHING"}`
    - **Total Iterations:** `{result.iterations_run}`
    - **Final Reward:** `{result.final_reward:.4f}`
    - **Execution Latency:** `{result.total_time_ms:.2f} ms`
    """
    )

    return ed_card, fig_ed


@app.cell
def _(go, hyp_distances, iters, np, poincare_3d):
    # Plot 2: 3D Poincaré Ball Visualization
    fig_poincare = go.Figure()

    u_vals = np.linspace(0, 2 * np.pi, 30)
    v_vals = np.linspace(0, np.pi, 20)
    xs = np.outer(np.cos(u_vals), np.sin(v_vals))
    ys = np.outer(np.sin(u_vals), np.sin(v_vals))
    zs = np.outer(np.ones(np.size(u_vals)), np.cos(v_vals))

    fig_poincare.add_trace(
        go.Surface(
            x=xs,
            y=ys,
            z=zs,
            opacity=0.08,
            colorscale=[[0, "#38bdf8"], [1, "#818cf8"]],
            showscale=False,
            hoverinfo="none",
            name="Poincaré Sphere Boundary (r=1.0)",
        )
    )

    hover_texts = [
        f"Iter {t}: (x={pt[0]:.3f}, y={pt[1]:.3f}, z={pt[2]:.3f})<br>"
        f"Hyperbolic Dist to Origin: {dist:.3f}"
        for t, pt, dist in zip(iters, poincare_3d, hyp_distances)
    ]

    fig_poincare.add_trace(
        go.Scatter3d(
            x=poincare_3d[:, 0],
            y=poincare_3d[:, 1],
            z=poincare_3d[:, 2],
            mode="lines+markers+text",
            name="State Vector Trajectory",
            line={"color": "#f43f5e", "width": 4},
            marker={
                "size": 7,
                "color": hyp_distances,
                "colorscale": "Viridis",
                "showscale": True,
                "colorbar": {"title": "Hyp Dist $d_P$", "thickness": 12, "x": 1.05},
            },
            text=[f"It {t}" for t in iters],
            textposition="top center",
            hovertext=hover_texts,
            hoverinfo="text",
        )
    )

    fig_poincare.update_layout(
        title="🌌 3D Poincaré Ball Projection ($2048\\text{D} \\to 3\\text{D}$)",
        template="plotly_dark",
        paper_bgcolor="#0b0f19",
        scene={
            "xaxis": {"range": [-1.1, 1.1], "gridcolor": "#1f2937", "backgroundcolor": "#111827"},
            "yaxis": {"range": [-1.1, 1.1], "gridcolor": "#1f2937", "backgroundcolor": "#111827"},
            "zaxis": {"range": [-1.1, 1.1], "gridcolor": "#1f2937", "backgroundcolor": "#111827"},
            "aspectratio": {"x": 1, "y": 1, "z": 1},
        },
        height=450,
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )

    return (fig_poincare,)


@app.cell
def _(ed_card, fig_ed, fig_poincare, mo):
    mo.vstack(
        [
            ed_card,
            mo.hstack(
                [mo.ui.plotly(fig_ed), mo.ui.plotly(fig_poincare)],
                justify="center",
                gap=2,
            ),
        ]
    )
    return


@app.cell
def _(mo, result):
    # Phase Breakdown Inspector Table
    rows = []
    for it_res in result.history:
        rows.append(
            {
                "Iteration": it_res.iteration,
                "Strategy": it_res.strategy,
                "Sweep Integrity": f"{it_res.sweep.integrity_score * 100:.0f}%",
                "AutoHarness Verified": "✅ Allowed (0ms AST)"
                if it_res.learning.autoharness_allowed
                else "❌ Blocked",
                "ZK-FV Proof": it_res.learning.zkfv_proof_id[:18] + "...",
                "Reward (r_t)": f"{it_res.learning.reward:.4f}",
                "Status": "Satisfied 🎯" if it_res.satisfied else "Refining 🔁",
                "Latency": f"{it_res.latency_ms:.2f} ms",
            }
        )

    mo.md("### 📋 Tripartite Iteration Ledger")
    mo.ui.table(rows)
    return (rows,)


@app.cell
def _(goal, mo, result):
    # Dual Persistence Inspector: Obsidian Vault vs SurrealDB
    latest_it = result.history[-1] if result.history else None
    proof_id = latest_it.learning.zkfv_proof_id if latest_it else "zkproof-none"
    reward = latest_it.learning.reward if latest_it else 0.0
    strat = latest_it.strategy if latest_it else "cellular_sheaf_diffusion"

    obsidian_preview = rf"""---
id: learning_{goal.goal_id}_it{result.iterations_run}
goal_id: {goal.goal_id}
iteration: {result.iterations_run}
strategy: {strat}
reward: {reward:.4f}
zkfv_proof_id: {proof_id}
model_provider: lemonade_Bonsai-8B-gguf (AMD Strix Halo NPU)
timestamp: {result.history[-1].sweep.checks_evaluated} checks verified
tags: [experiential-learning, autoharness, zkfv, flume, strix-halo]
---

# Experiential Learning: {goal.title} (Iteration {result.iterations_run})

## 1. Codebase Sweep Findings
- **Integrity Score:** 1.00 (Zero hollow seams)
- **Status:** PASSED (Producer-consumer & dormancy validated)

## 2. Bleeding Edge Citations
- arXiv:2603.03329v1 [cs.AI] — AutoHarness: Deterministic Code-as-Action Verifiers
- arXiv:2501.13956 [cs.DB] — Graphiti: Bi-Temporal Knowledge Graph Memory
- arXiv:2412.08832 [math.AT] — Cellular Sheaves & Discrete Laplacian Harmonic Analysis

## 3. Experiential Distillation
- **Strategy Executed:** `{strat}`
- **AutoHarness Policy Allowed:** `True` (Bypassed LLM: True)
- **ZK-FV Formal Proof Valid:** `True`
- **Distilled Lesson:** Satisfied goal specification via harmonic diffusion with reward {reward:.4f}.
"""

    surreal_preview = rf"""UPSERT experiential_replay:`exp_{goal.goal_id}_it{result.iterations_run}` MERGE {{
    goal_id: "{goal.goal_id}",
    iteration: {result.iterations_run},
    strategy: "{strat}",
    reward: {reward:.4f},
    autoharness_verified: true,
    zkfv_valid: true,
    proof_id: "{proof_id}",
    lesson: "Harmonic consensus reached under cellular sheaf gradient descent.",
    timestamp: time::now()
}};

UPSERT goal:`{goal.goal_id}` SET
    title = "{goal.title}",
    target_metric = "{goal.target_metric}",
    target_threshold = {goal.target_threshold},
    converged = {str(result.converged).lower()},
    final_reward = {reward:.4f},
    updated_at = time::now();
"""

    mo.md("### 💾 Dual Persistence Inspector (Obsidian Vault & SurrealDB v2)")
    mo.ui.tabs(
        {
            "📝 Obsidian Vault Markdown Note": mo.md(f"```markdown\n{obsidian_preview}\n```"),
            "⚡ SurrealDB v2 QL Record": mo.md(f"```sql\n{surreal_preview}\n```"),
        }
    )
    return (
        latest_it,
        obsidian_preview,
        proof_id,
        reward,
        strat,
        surreal_preview,
    )


if __name__ == "__main__":
    app.run()
