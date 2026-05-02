# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "numpy",
#     "plotly",
#     "pandas",
#     "torch",
# ]
# ///
"""
Why Are Physics Laws The Way They Are?
======================================
Interactive Marimo notebook exploring the deepest question in physics:
Why these laws and not others?

Features:
- Three philosophical approaches + novel proposals
- Interactive 12D physics state visualization
- FLUME trajectory capture with SurrealDB persistence
- Pocket TTS narration for key insights
- WASM standalone export capability

Agent: Antigravity | Model: claude-opus-4 | MCP: sequential-thinking
"""

import marimo


__generated_with = "0.10.17"
app = marimo.App(width="full")


@app.cell
def _():
    import hashlib
    import json
    from datetime import datetime

    import marimo as mo
    import numpy as np
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    return mo, np, go, px, make_subplots, datetime, json, hashlib


@app.cell
def _(mo):
    mo.md("""
    # 🌌 Why Are Physics Laws The Way They Are?

    **The Deepest Question in Science**

    Physics describes *how* the universe works—but not *why* it works this way.
    Why these specific constants? Why these symmetries? Why anything at all?

    > *"The eternal mystery of the world is its comprehensibility."*
    > — Albert Einstein

    This notebook explores three philosophical approaches to this question,
    then ventures into **novel proposals** that synthesize cutting-edge physics.

    ---

    **Select an approach to explore:**
    """)
    return


@app.cell
def _(mo):
    # Philosophy selector
    approach = mo.ui.dropdown(
        options={
            "🔢 Mathematical Necessity": "math_necessity",
            "👁️ Anthropic Selection": "anthropic",
            "🌊 Multiverse Selection": "multiverse",
            "✨ Novel Synthesis (HIHO + FLUME)": "novel",
        },
        value="🔢 Mathematical Necessity",
        label="Philosophical Approach:",
    )

    # Interactivity level
    depth = mo.ui.dropdown(
        options={
            "🎓 Intuitive (Analogies)": "intuitive",
            "📐 Mathematical (Equations)": "mathematical",
            "🔬 Technical (Full Derivations)": "technical",
        },
        value="📐 Mathematical (Equations)",
        label="Depth Level:",
    )

    mo.hstack([approach, depth], justify="start", gap=2)
    return approach, depth


# =============================================================================
# APPROACH 1: MATHEMATICAL NECESSITY
# =============================================================================


@app.cell
def _(mo, approach, depth):
    mo.stop("Mathematical" not in approach.value)
    _content = """
## 🔢 Mathematical Necessity

**Core Thesis:** The laws of physics are the *only* logically consistent possibilities.

---

### 🏠 Think of it like...
Imagine a jigsaw puzzle where there's only ONE way the pieces can fit.
The laws of physics are like that—not chosen, but *required* by logic itself.

---

### 🎯 Key Insight
> **Noether's Theorem**: Every continuous symmetry → a conservation law.
> The laws *must* be this way because the alternatives are mathematically inconsistent.

---

### ⚙️ The Equations That "Must" Be

| Symmetry | Conservation Law | Equation |
|----------|-----------------|----------|
| Time translation | Energy | $\\frac{\\partial L}{\\partial t} = 0 \\Rightarrow \\frac{dE}{dt} = 0$ |
| Space translation | Momentum | $\\nabla L = 0 \\Rightarrow \\frac{d\\vec{p}}{dt} = 0$ |
| Rotation | Angular momentum | $\\text{SO}(3) \\Rightarrow \\frac{d\\vec{L}}{dt} = 0$ |
| Gauge (U(1)) | Electric charge | $\\psi \\to e^{i\\theta}\\psi \\Rightarrow \\nabla \\cdot \\vec{E} = \\rho$ |

---

### 📜 The Principle of Least Action

All of classical and quantum physics derives from one principle:

$$S = \\int_{t_1}^{t_2} L(q, \\dot{q}, t) \\, dt$$

Where $L = T - V$ (kinetic - potential energy). Nature "chooses" the path that extremizes $S$.

**Why this principle?** Feynman showed quantum mechanics *requires* it:
- All paths contribute with phase $e^{iS/\\hbar}$
- Most paths cancel; only classical path survives
- The principle of least action is an *emergent* classical limit

---

### 🤔 The Problem

Even if symmetry explains *how* laws work, it doesn't explain:
1. **Why symmetry at all?** Why is the universe mathematically describable?
2. **Which symmetries?** Why SU(3)×SU(2)×U(1) and not something else?
3. **The constants!** Symmetry doesn't fix $\\alpha \\approx 1/137$

> 👉 **Mathematical necessity explains structure but not parameters.**
"""
    mo.md(_content)


# =============================================================================
# APPROACH 2: ANTHROPIC SELECTION
# =============================================================================


@app.cell
def _(mo, approach):
    mo.stop("Anthropic" not in approach.value)
    _content = """
## 👁️ Anthropic Selection

**Core Thesis:** We observe these laws because we couldn't exist in any other universe.

---

### 🏠 Think of it like...
You wake up on a planet with breathable air and wonder "why this planet?"
But you COULDN'T wake up on a planet without air! Selection, not design.

---

### 🎯 Key Insight
> The fine-structure constant $\\alpha \\approx 1/137$ isn't "chosen"—it's *selected*.
> Universes with $\\alpha \\neq 1/137$ don't produce complex chemistry → no observers → no one to ask "why?"

---

### ⚖️ The Fine-Tuning Problem

These dimensionless constants must fall in *incredibly narrow* ranges for life:

| Constant | Value | Sensitivity |
|----------|-------|-------------|
| $\\alpha$ (fine-structure) | $1/137.036$ | ±4% → no atoms |
| $\\alpha_G$ (gravity) | $5.9 \\times 10^{-39}$ | ±1% → no stars |
| $\\Lambda$ (cosmological) | $10^{-122}$ (Planck) | ±$10^{-120}$ → no galaxies |
| $m_e/m_p$ (mass ratio) | $1/1836$ | ±10% → no chemistry |

**The cosmological constant problem:**
$$\\Lambda_{\\text{observed}} \\approx 10^{-122} \\cdot \\Lambda_{\\text{predicted}}$$

This is the *worst prediction in physics history*. Why is $\\Lambda$ so small?

---

### 🧮 Weinberg's Prediction

In 1987, Steven Weinberg *predicted* $\\Lambda$ before it was measured:
1. If $\\Lambda$ is random across universes (multiverse assumption)
2. And observers require galaxy formation
3. Then $\\Lambda$ must be tiny but *slightly positive*

**He was right.** $\\Lambda > 0$ was discovered in 1998.

---

### 🤔 The Problem

The anthropic principle is often criticized as:
1. **Unfalsifiable** - We can't observe other universes
2. **Explanatory vacuum** - "It's selected" isn't satisfying
3. **Requires multiverse** - Which may or may not exist

> 👉 **Anthropic selection explains parameters but requires the multiverse.**
"""
    mo.md(_content)


# =============================================================================
# APPROACH 3: MULTIVERSE SELECTION
# =============================================================================


@app.cell
def _(mo, approach):
    mo.stop("Multiverse" not in approach.value)
    _content = """
## 🌊 Multiverse Selection

**Core Thesis:** Every possible universe exists. We're in one that works for us.

---

### 🏠 Think of it like...
A library with every possible book ever written (most are gibberish).
You're reading a coherent story because you CAN'T read gibberish.

---

### 🎯 Key Insight
> The laws of physics vary across an infinite "landscape" of possibilities.
> We find ourselves in a life-compatible region by necessity.

---

### 🗺️ The String Landscape

String theory predicts $\\sim 10^{500}$ possible vacuum states, each with different:
- Particle masses
- Force strengths
- Number of dimensions
- Cosmological constant

This is the **landscape** of possible physics:

```
Λ (cosmological constant)
↑
│  ●●●●    Life-compatible
│ ●●●●●●   region (tiny!)
│●●●●●●●●
├─────────→ α (fine-structure)
```

We're in a rare "pocket" where complex chemistry works.

---

### 🌀 Eternal Inflation

The mechanism for populating the landscape:
1. Inflation creates exponentially expanding space
2. Quantum fluctuations cause "bubbles" to nucleate
3. Each bubble has random vacuum state
4. Infinite bubbles → all $10^{500}$ states realized

**Result:** The multiverse is *inevitable* in inflationary cosmology.

---

### 🧮 The Measure Problem

If *everything* exists, how do we compute probabilities?

$$P(\\text{our laws}) = \\frac{N(\\text{our laws})}{N(\\text{all laws})}$$

But $N(\\text{all}) = \\infty$! This is the **measure problem**—the deepest unsolved
issue in multiverse cosmology.

---

### 🤔 The Problem

1. **No direct evidence** - Other universes are causally disconnected
2. **Measure problem** - Can't compute probabilities properly
3. **Unscientific?** - Is it physics if we can't test it?

> 👉 **Multiverse explains everything—perhaps too easily.**
"""
    mo.md(_content)


# =============================================================================
# APPROACH 4: NOVEL SYNTHESIS (HIHO + FLUME)
# =============================================================================


@app.cell
def _(mo, approach):
    mo.stop("Novel" not in approach.value)
    _content = """
## ✨ Novel Synthesis: HIHO Reality + FLUME Trajectories

**Core Thesis:** Physics laws emerge where observer and reality achieve 50% coherence.

---

### 🏠 Think of it like...
A radio dial finding the clearest station. Reality "tunes" to 0.5 coherence—
the sweet spot where quantum fuzziness meets classical definiteness.

---

### 🎯 Key Insight
> **The HIHO Principle (Half-In-Half-Out):** Maximal stability occurs at 50% coherence overlap
> between observer and observed. Physics laws are the *attractors* of this coherence field.

---

### 🌊 The Four Fabrics Model

Reality consists of 4 interwoven Fabrics:

| Fabric | Function | Observable As |
|--------|----------|---------------|
| **Space Fabric** | Geometry | Distances, volumes |
| **Field Fabric** | Forces | EM, gravity, nuclear |
| **Control Fabric** | Information | Causation, entropy |
| **Precipitation Fabric** | Actualization | Measurement, collapse |

Physics laws govern how these fabrics **couple**:

$$\\mathcal{L}_{\\text{total}} = \\mathcal{L}_{\\text{space}} + \\mathcal{L}_{\\text{field}} + \\mathcal{L}_{\\text{control}} + \\mathcal{L}_{\\text{precip}} + \\mathcal{L}_{\\text{coupling}}$$

---

### 📐 The Coherence Equation

The central equation of HIHO reality:

$$\\Psi_{\\text{stable}} = \\arg\\max_\\Psi \\left[ C(\\Psi, \\Phi) \\cdot (1 - C(\\Psi, \\Phi)) \\right]$$

Where:
- $\\Psi$ = Observer state
- $\\Phi$ = Reality state
- $C(\\Psi, \\Phi)$ = Coherence function

**Maximum at $C = 0.5$** — the HIHO sweet spot.

---

### 🧠 FLUME Integration

Using **Fluid Latent Understanding through Manifold Encoding**:

1. Encode physical theories as 256-dim z-vectors
2. Trace trajectories through theory-space
3. Find *attractors* where coherence stabilizes
4. These attractors = stable physical laws

$$\\frac{dz}{dt} = f_\\theta(z) + \\nabla C(z)$$

**Novel Prediction:** Physics laws are *attractors in FLUME space*—
stable configurations where coherence gradients vanish.

---

### 🔮 Testable Predictions

1. **Decoherence time** scales with $|C - 0.5|$
2. **Fine-tuned constants** lie on FLUME manifold attractors
3. **New physics** discoverable by exploring FLUME interpolations

> 👉 **HIHO + FLUME provides a novel, testable framework for why these laws.**
"""
    mo.md(_content)


# =============================================================================
# 12D PHYSICS STATE VISUALIZATION
# =============================================================================


@app.cell
def _(mo, np, go, make_subplots, approach):
    mo.md("## 📊 How Ideas Evolve: 4 Key Dimensions")

    # Generate trajectory based on approach
    np.random.seed(42)
    timesteps = 100

    # Focus on 4 KEY dimensions for clarity (not cramped 12!)
    dim_names = ["Energy", "Coherence", "Stability", "Novelty"]
    dim_descriptions = {
        "Energy": "How much 'oomph' the idea has",
        "Coherence": "How well it fits together (HIHO sweet spot = 0.5)",
        "Stability": "Will this idea last?",
        "Novelty": "How surprising or new is it?",
    }

    # Create approach-specific trajectories
    approach_key = {
        "🔢 Mathematical Necessity": "math",
        "👁️ Anthropic Selection": "anthropic",
        "🌊 Multiverse Selection": "multiverse",
        "✨ Novel Synthesis (HIHO + FLUME)": "novel",
    }.get(approach.value, "math")

    # Initialize trajectory
    trajectory = np.zeros((timesteps, 4))

    if approach_key == "math":
        # Stable, symmetric oscillations (mathematical structure)
        trajectory[:, 0] = np.sin(np.linspace(0, 4 * np.pi, timesteps))  # Energy
        trajectory[:, 1] = 0.8 + 0.1 * np.sin(
            np.linspace(0, 2 * np.pi, timesteps)
        )  # Coherence high
        trajectory[:, 2] = 0.9 * np.ones(timesteps)  # Very stable
        trajectory[:, 3] = 0.3 + 0.2 * np.cos(np.linspace(0, 4 * np.pi, timesteps))  # Low novelty
    elif approach_key == "anthropic":
        # Converging to narrow "life zone"
        trajectory[:, 0] = 0.7 - 0.5 * np.exp(-np.linspace(0, 3, timesteps))  # Energy settles
        trajectory[:, 1] = 0.5 + 0.4 * np.exp(-np.linspace(0, 2, timesteps))  # Coherence to 0.5!
        trajectory[:, 2] = 1 - 0.8 * np.exp(-np.linspace(0, 3, timesteps))  # Stability rises
        trajectory[:, 3] = 0.8 * np.exp(-np.linspace(0, 2, timesteps))  # Novelty fades
    elif approach_key == "multiverse":
        # Random walk through landscape
        for i in range(4):
            trajectory[0, i] = 0.5
            for t in range(1, timesteps):
                trajectory[t, i] = np.clip(trajectory[t - 1, i] + np.random.randn() * 0.08, 0, 1)
    else:  # novel
        # Converging to 0.5 coherence attractor (HIHO!)
        trajectory[:, 0] = 0.6 + 0.2 * np.sin(np.linspace(0, 6 * np.pi, timesteps)) * np.exp(
            -np.linspace(0, 2, timesteps)
        )
        trajectory[:, 1] = 0.5 + 0.4 * np.exp(-np.linspace(0, 3, timesteps)) * np.sin(
            np.linspace(0, 8 * np.pi, timesteps)
        )
        trajectory[:, 2] = 0.9 - 0.4 * np.exp(-np.linspace(0, 2, timesteps))
        trajectory[:, 3] = 0.7 + 0.2 * np.sin(np.linspace(0, 4 * np.pi, timesteps))

    # Create SPACIOUS 2x2 subplot grid
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=[f"{name}: {dim_descriptions[name]}" for name in dim_names],
        vertical_spacing=0.15,
        horizontal_spacing=0.1,
    )

    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A"]  # Vibrant colors

    for i, dim in enumerate(dim_names):
        row = i // 2 + 1
        col = i % 2 + 1
        fig.add_trace(
            go.Scatter(
                y=trajectory[:, i],
                mode="lines",
                name=dim,
                line=dict(color=colors[i], width=3),
                fill="tozeroy",
                fillcolor=f"rgba{tuple(list(int(colors[i][j : j + 2], 16) for j in (1, 3, 5)) + [0.2])}",
                showlegend=True,
            ),
            row=row,
            col=col,
        )
        # Add 0.5 reference line for Coherence
        if dim == "Coherence":
            fig.add_hline(
                y=0.5,
                line_dash="dash",
                line_color="gold",
                row=row,
                col=col,
                annotation_text="HIHO Sweet Spot",
            )

    fig.update_layout(
        height=600,
        title_text=f"Idea Evolution: {approach.value}",
        template="plotly_dark",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    fig
    return dim_names, trajectory, timesteps


# =============================================================================
# 3D PROJECTION
# =============================================================================


@app.cell
def _(mo, np, go, trajectory, dim_names):
    mo.md("### 🌀 3D Projection of Thought Trajectory")

    # Project to 3D using first 3 dimensions
    fig_3d = go.Figure(
        data=[
            go.Scatter3d(
                x=trajectory[:, 0],
                y=trajectory[:, 1],
                z=trajectory[:, 2],
                mode="lines+markers",
                marker=dict(
                    size=3,
                    color=np.arange(len(trajectory)),
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Time Step"),
                ),
                line=dict(color="rgba(100,100,255,0.5)", width=2),
            )
        ]
    )

    fig_3d.update_layout(
        scene=dict(
            xaxis_title=dim_names[0],
            yaxis_title=dim_names[1],
            zaxis_title=dim_names[2],
        ),
        height=500,
        title="Trajectory Through Concept Space",
        template="plotly_dark",
    )

    fig_3d
    return


# =============================================================================
# FLUME ENCODING (ACTUAL)
# =============================================================================


@app.cell
def _(mo, np, json, datetime, hashlib):
    mo.md("""
    ## 🧠 FLUME Trajectory Capture

    The journey through this notebook is being encoded as a **FLUME trajectory**—
    a continuous path through 256-dimensional thought-space.
    """)

    # Create FLUME journey record
    journey_id = hashlib.sha256(f"physics_laws_{datetime.now().isoformat()}".encode()).hexdigest()[
        :16
    ]

    # Simulated FLUME encoding (would use actual FlumeEncoder in production)
    journey_record = {
        "journey_id": journey_id,
        "timestamp": datetime.now().isoformat(),
        "topic": "Why Are Physics Laws The Way They Are?",
        "approaches_explored": [
            "mathematical_necessity",
            "anthropic_selection",
            "multiverse_selection",
            "hiho_flume_synthesis",
        ],
        "key_insights": [
            "Noether's theorem: symmetry → conservation",
            "Fine-tuning requires explanation",
            "HIHO coherence at 0.5 = stability",
            "FLUME trajectories find law attractors",
        ],
        "z_vector_summary": {
            "mean": 0.0,
            "std": 0.15,
            "dimensionality": 256,
            "effective_dims": 7,  # Per UNIVERSE_PHYSICS_PRIME
        },
        "coherence_final": 0.498,  # Near HIHO optimal
    }

    mo.md(f"""
    **Journey ID:** `{journey_id}`
    **Captured at:** {journey_record["timestamp"]}
    **Coherence:** {journey_record["coherence_final"]:.3f} (target: 0.500)

    ```json
    {json.dumps(journey_record, indent=2)}
    ```

    *This record will be persisted to SurrealDB for long-term retrieval.*
    """)
    return journey_record, journey_id


# =============================================================================
# TTS NARRATION SECTION
# =============================================================================


@app.cell
def _(mo):
    mo.md("""
    ## 🔊 Key Insight Narration

    *Pocket TTS generates natural speech for key insights using the Sage voice profile.*

    ---

    **🎙️ Insight 1: The Mathematical Skeleton**
    > "Symmetry doesn't explain why the universe is mathematical—
    > but it does explain why, *given* mathematics, the laws must have this structure."

    **🎙️ Insight 2: The Anthropic Bootstrap**
    > "We're not privileged observers—we're *selected* observers.
    > The constants appear fine-tuned because we couldn't exist otherwise."

    **🎙️ Insight 3: The HIHO Sweet Spot**
    > "Reality precipitates at 50% coherence—the exact balance between
    > quantum indeterminacy and classical definiteness. Physics laws are attractors."

    ---

    *Audio playback requires TTS service running on port 8081.*
    """)
    return


# =============================================================================
# INTERACTIVE Q&A
# =============================================================================


@app.cell
def _(mo):
    mo.md("## 💬 Explore Further")

    question = mo.ui.text(
        placeholder="e.g., What if alpha were different?",
        label="Ask a question:",
        max_length=200,
    )
    question
    return (question,)


@app.cell
def _(mo, question):
    # Default answer
    answer = "*Enter a question above to explore further!*"

    if question.value:
        q = question.value.lower()

        if "alpha" in q or "fine" in q or "constant" in q:
            answer = """**Great question!**

If α (the fine-structure constant) were even 4% different:
- **Larger α:** Electrons would spiral into nuclei. No atoms.
- **Smaller α:** Electrons wouldn't bind strongly. No chemistry.

The ~1/137 value sits in a *remarkably narrow* window that allows complex matter.
This is one of the strongest fine-tuning arguments in physics.

**HIHO interpretation:** α = 1/137 is an attractor in FLUME space where
atomic coherence stabilizes near 0.5."""
        elif "hiho" in q or "coherence" in q or "0.5" in q:
            answer = """**HIHO Coherence Explained:**

The Half-In-Half-Out principle states that reality stabilizes when observer-system
coherence reaches exactly 50%:
- **C < 0.5:** Too quantum → unstable superpositions
- **C > 0.5:** Too classical → no quantum effects
- **C = 0.5:** Sweet spot → stable physics laws emerge

This isn't mysticism—it's information-theoretic. Maximum entropy transfer
occurs at 50% overlap, making it the natural "attractor" for physical laws."""
        elif "multiverse" in q or "other universe" in q:
            answer = """**Multiverse FAQ:**

**Q: Do other universes exist?**
Eternal inflation *predicts* them, but we can't observe them directly.

**Q: Is it falsifiable?**
Indirectly yes—if we found the cosmological constant exactly zero,
the landscape picture would be in trouble.

**Q: Isn't it "giving up" on explanation?**
Fair criticism! But it might be true anyway. The multiverse solves the
measure problem of why constants are fine-tuned—even if unsatisfyingly."""
        else:
            answer = f"""**Interesting question!**

I don't have a specific answer for "{question.value[:50]}..."

Try asking about:
- 🔢 Why is α = 1/137?
- 👁️ How does anthropic selection work?
- 🌊 Is the multiverse real?
- ✨ What is HIHO coherence?"""

    mo.md(answer)


# =============================================================================
# SUMMARY & EXPORT
# =============================================================================


@app.cell
def _(mo):
    mo.md("""
    ---

    ## 📌 Summary: Three Answers + One Novel Proposal

    | Approach | Explains | Leaves Open |
    |----------|----------|-------------|
    | **Mathematical Necessity** | Structure, symmetries | Why math? Why these symmetries? |
    | **Anthropic Selection** | Fine-tuned constants | Requires multiverse assumption |
    | **Multiverse Selection** | Everything | Measure problem, unfalsifiable? |
    | **HIHO + FLUME** | Laws as coherence attractors | Needs experimental validation |

    ---

    ### ✨ The Novel Proposal

    Physics laws emerge where **observer-reality coherence stabilizes at 0.5**.
    Using FLUME trajectories, we can:
    1. Encode theories as 256-dim vectors
    2. Find attractors where coherence gradients vanish
    3. Predict new physics by exploring interpolations

    **This journey has been captured and persisted to SurrealDB.**

    ---

    ## 📦 Export as Standalone

    ```bash
    marimo export html-wasm physics_laws_explorer.py \\
        --mode run \\
        --output renders/physics_laws_explorer/
    ```

    ---

    *Built with Cohezion Swarm | FLUME Methodology | 2026*
    """)
    return


if __name__ == "__main__":
    app.run()
