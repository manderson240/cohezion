"""Cohezion Compound Loop Metrics — Interactive Walkthrough.

Reactive marimo notebook exploring the compound engineering loop:
Executor → SkillRefiner → RetrospectionEngine → Updated Skill.

Visualises quality scores, cache hit rates, and tier latency over
synthetic-but-realistic compound loop execution data.
"""

import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium", app_title="Cohezion Compound Loop")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(
        r"""
        # Cohezion Compound Loop Metrics

        The **compound engineering loop** continuously refines skills:

        ```
        PRIME Skill → InstructionExpander → PlanExecutor
            → ExecutionOrchestrator (11-step pipeline)
            → RetrospectionEngine → SkillRefiner → Updated Skill
        ```

        Adjust the controls below to explore different execution windows.
        """
    )
    return ()


@app.cell
def _(mo):
    n_cycles = mo.ui.slider(
        10, 200, step=10, value=50, label="Simulation cycles"
    )
    seed_val = mo.ui.slider(0, 99, step=1, value=42, label="Random seed")
    mo.hstack([n_cycles, seed_val], justify="start")
    return n_cycles, seed_val


@app.cell
def _(mo, n_cycles, seed_val):
    mo.md(f"**Running {n_cycles.value} cycles** (seed={seed_val.value})")
    return ()


@app.cell
def _(n_cycles, seed_val):
    """Generate synthetic compound loop metrics (realistic distributions)."""
    import random
    import math

    random.seed(seed_val.value)
    n = n_cycles.value

    cycles = list(range(1, n + 1))

    # Quality converges toward HIHO 0.5 equilibrium from random start
    quality = []
    q = random.uniform(0.2, 0.8)
    for i in range(n):
        noise = random.gauss(0, 0.04)
        q = q + 0.03 * (0.5 - q) + noise  # mean-reversion to HIHO 0.5
        quality.append(max(0.0, min(1.0, q)))

    # Cache hit rate ramps up as the semantic cache warms
    cache_hits = [min(0.95, 0.1 + 0.85 * (1 - math.exp(-i / (n * 0.3))) +
                      random.gauss(0, 0.02)) for i in range(n)]

    # Latency: NPU fast (24ms), iGPU medium (200ms), CPU slow (800ms)
    tier_weights = [(0.7, 24), (0.2, 200), (0.1, 800)]
    latency_ms = []
    for _ in range(n):
        r = random.random()
        cumulative = 0
        for w, base_ms in tier_weights:
            cumulative += w
            if r < cumulative:
                latency_ms.append(base_ms + random.gauss(0, base_ms * 0.1))
                break

    # Skill refinement confidence (increases as SkillRefiner accumulates data)
    confidence = [min(0.95, 0.4 + 0.55 * (i / n) + random.gauss(0, 0.03))
                  for i in range(n)]

    return cache_hits, confidence, cycles, latency_ms, quality


@app.cell
def _(mo):
    chart_type = mo.ui.dropdown(
        ["Quality Score", "Cache Hit Rate", "Latency (ms)", "All"],
        value="All",
        label="Chart",
    )
    mo.vstack([chart_type])
    return (chart_type,)


@app.cell
def _(cache_hits, chart_type, confidence, cycles, latency_ms, mo, quality):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    sel = chart_type.value

    if sel == "All":
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Quality Score (HIHO target = 0.5)",
                "Semantic Cache Hit Rate",
                "Tier Latency (ms)",
                "SkillRefiner Confidence",
            ),
        )
        fig.add_trace(
            go.Scatter(x=cycles, y=quality, mode="lines", name="quality",
                       line=dict(color="#4C78A8")),
            row=1, col=1,
        )
        fig.add_hline(y=0.5, line_dash="dash", line_color="orange",
                      annotation_text="HIHO equilibrium", row=1, col=1)
        fig.add_trace(
            go.Scatter(x=cycles, y=cache_hits, mode="lines", name="cache",
                       line=dict(color="#72B7B2")),
            row=1, col=2,
        )
        fig.add_trace(
            go.Scatter(x=cycles, y=latency_ms, mode="markers", name="latency",
                       marker=dict(color="#F58518", size=4)),
            row=2, col=1,
        )
        fig.add_trace(
            go.Scatter(x=cycles, y=confidence, mode="lines", name="confidence",
                       line=dict(color="#E45756")),
            row=2, col=2,
        )
        fig.update_layout(height=500, showlegend=False,
                          title_text="Compound Loop Metrics Dashboard")
    elif sel == "Quality Score":
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cycles, y=quality, mode="lines+markers",
                                 name="quality", line=dict(color="#4C78A8")))
        fig.add_hline(y=0.5, line_dash="dash", line_color="orange",
                      annotation_text="HIHO equilibrium (0.50)")
        fig.update_layout(title="Quality Score", xaxis_title="Cycle",
                          yaxis_title="Score", height=400)
    elif sel == "Cache Hit Rate":
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cycles, y=cache_hits, mode="lines",
                                 fill="tozeroy", line=dict(color="#72B7B2")))
        fig.update_layout(title="Semantic Cache Hit Rate", xaxis_title="Cycle",
                          yaxis_title="Hit Rate", yaxis_range=[0, 1], height=400)
    elif sel == "Latency (ms)":
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cycles, y=latency_ms, mode="markers",
                                 marker=dict(color="#F58518", size=5)))
        fig.add_hline(y=24, line_dash="dot", annotation_text="NPU (24ms)")
        fig.add_hline(y=200, line_dash="dot", annotation_text="iGPU (200ms)")
        fig.add_hline(y=800, line_dash="dot", annotation_text="CPU (800ms)")
        fig.update_layout(title="Tier Latency", xaxis_title="Cycle",
                          yaxis_title="ms", height=400)
    else:
        fig = go.Figure()

    mo.ui.plotly(fig)
    return (fig,)


@app.cell
def _(cache_hits, confidence, latency_ms, mo, quality):
    avg_q = sum(quality) / len(quality)
    avg_cache = sum(cache_hits) / len(cache_hits)
    avg_lat = sum(latency_ms) / len(latency_ms)
    avg_conf = sum(confidence) / len(confidence)

    mo.md(
        f"""
        ## Summary Statistics

        | Metric | Mean | Notes |
        |--------|------|-------|
        | Quality score | **{avg_q:.3f}** | HIHO target = 0.500 |
        | Cache hit rate | **{avg_cache:.1%}** | L1+L2+L3 combined |
        | Avg latency | **{avg_lat:.0f} ms** | NPU/iGPU/CPU blended |
        | SkillRefiner confidence | **{avg_conf:.3f}** | Converges to ≥0.90 |

        > The compound loop self-improves over time — quality drifts toward
        > the HIHO equilibrium (0.5) and cache hit rate climbs as the semantic
        > cache warms with recurring patterns.
        """
    )
    return avg_cache, avg_conf, avg_lat, avg_q


@app.cell
def _(mo):
    import os
    _default_url = os.getenv("LEMONADE_URL", "http://localhost:13305")
    loop_query = mo.ui.text_area(
        placeholder="Ask about HIHO equilibrium, cache hit rates, tier routing...",
        label="Ask the local agent (AMD silicon, $0)",
        rows=3,
    )
    loop_model = mo.ui.dropdown(
        ["llama3.2-1b-FLM", "Bonsai-8B-gguf", "DeepSeek-Qwen3-8B-GGUF"],
        value="llama3.2-1b-FLM",
        label="Model",
    )
    loop_run = mo.ui.run_button(label="Ask Agent ▶")
    loop_url = mo.ui.text(value=_default_url, label="Lemonade URL")
    mo.vstack([
        mo.md("## Live Agent — Ask About the Compound Loop"),
        mo.hstack([loop_url, loop_model], justify="start"),
        loop_query,
        loop_run,
    ])
    return loop_model, loop_query, loop_run, loop_url


@app.cell
def _(loop_model, loop_query, loop_run, loop_url, mo):
    import requests as _req

    mo.stop(not loop_run.value, mo.md("_Configure a query above, then click **Ask Agent ▶**_"))

    def _ask(q: str, model: str, base_url: str) -> str:
        try:
            r = _req.post(
                f"{base_url.rstrip('/')}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": (
                            "You are an expert in Cohezion compound AI engineering loops. "
                            "Answer concisely with reference to HIHO (Half-In-Half-Out) "
                            "equilibrium, semantic cache, and tiered AMD inference."
                        )},
                        {"role": "user", "content": q},
                    ],
                    "max_tokens": 600,
                },
                timeout=90,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            return f"⚠️ Lemonade error: {exc}"

    _answer = _ask(loop_query.value, loop_model.value, loop_url.value)
    mo.callout(mo.md(_answer), kind="info")
    return ()


if __name__ == "__main__":
    app.run()
