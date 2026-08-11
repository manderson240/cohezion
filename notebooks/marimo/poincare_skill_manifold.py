import marimo

__generated_with = "0.1.0"
app = marimo.App(width="full")


@app.cell
def __():
    import marimo as mo
    import numpy as np
    import plotly.graph_objects as go

    from cohezion.flume.poincare_manifold_visualizer import (
        PoincareManifoldVisualizer,
        compute_hyperbolic_distance,
        generate_poincare_figure,
        project_2048d_to_poincare_3d,
    )

    return (
        PoincareManifoldVisualizer,
        compute_hyperbolic_distance,
        generate_poincare_figure,
        mo,
        np,
        go,
        project_2048d_to_poincare_3d,
    )


@app.cell
def __(mo):
    mo.md(
        """
        # 🌌 Poincaré 2048D Hyperbolic Skill & Retrospective Manifold

        Visualizing Cohezion's 71 PRIME Skills and SurrealDB Retrospectives inside the 3D Poincaré Ball:

        $$d_P(u, v) = \\text{arcosh}\\left(1 + 2 \\frac{\\|u-v\\|^2}{(1-\\|u\\|^2)(1-\\|v\\|^2)}\\right)$$
        """
    )
    return


@app.cell
def __(PoincareManifoldVisualizer):
    viz = PoincareManifoldVisualizer(seed=42)
    skills = viz.load_cohezion_skills(max_skills=71)
    retros = viz.load_surreal_retrospectives(count=15)
    return retros, skills, viz


@app.cell
def __(generate_poincare_figure, retros, skills):
    fig = generate_poincare_figure(skills_data=skills, retros_data=retros)
    return (fig,)


@app.cell
def __(fig, mo):
    mo.plotly(fig)
    return


@app.cell
def __(mo, skills):
    skills_summary = [
        {
            "Skill Name": s["name"],
            "Domain": s["domain"],
            "2048D Norm": round(s["norm_2048d"], 4),
            "Hyperbolic Distance to Origin": round(s["hyp_dist_origin"], 4),
        }
        for s in skills[:10]
    ]
    mo.md("### 📊 Top 10 Skill Coordinates in Poincaré Ball")
    mo.table(skills_summary)
    return (skills_summary,)


if __name__ == "__main__":
    app.run()
