"""ThermodynamicGravity ε Sweep — Interactive Walkthrough.

Reactive marimo notebook exploring the thermodynamic gravity model
(Isichei & Magueijo 2026, arXiv:2511.22221, PRL).

GR emerges as a degenerate Otto thermodynamic cycle (ε=0).
Adding work-producing legs with Lorentz violation parameter ε > 0
generates late-time cosmic acceleration without a cosmological constant Λ.

Wired into Cohezion cosmogony Step 3→4:
SO(12) Symmetric Vacuum → Fabric Differentiation.
"""

import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium", app_title="ThermodynamicGravity ε Sweep")


@app.cell
def _():
    import math

    import marimo as mo
    import plotly.graph_objects as go

    return go, math, mo


@app.cell
def _(mo):
    mo.md(
        r"""
        # ThermodynamicGravity ε Sweep

        **Paper:** Isichei & Magueijo (2026) — *arXiv:2511.22221* (PRL)

        | ε | Otto cycle | Physical consequence |
        |---|-----------|---------------------|
        | 0 | Degenerate | Standard GR, Λ = 0 |
        | 0 < ε < 1 | Non-degenerate | Late-time acceleration, ∂_μT^μν ≠ 0 |
        | 1 | Maximal | Maximum departure from LLI |

        **Harness invariant LV1** requires `ε = 0` in production Cohezion runs.
        This sweep lets you explore what happens when you dial ε up.
        """
    )
    return ()


@app.cell
def _(mo):
    epsilon = mo.ui.slider(
        0.0, 1.0, step=0.01, value=0.0,
        label="ε — Lorentz violation parameter", show_value=True,
    )
    temperature = mo.ui.slider(
        0.1, 5.0, step=0.1, value=1.0,
        label="T — Temperature (natural units)", show_value=True,
    )
    n_legs = mo.ui.slider(
        1, 10, step=1, value=3,
        label="N — Work-producing legs in Otto cycle",
    )
    mo.vstack([epsilon, mo.hstack([temperature, n_legs], justify="start")])
    return epsilon, n_legs, temperature


@app.cell
def _(epsilon, math, mo, n_legs, temperature):
    """Evaluate the actual ThermodynamicGravity dataclass."""
    try:
        from cohezion.physics.thermodynamic_gravity import ThermodynamicGravity, OttoWorkLeg
        _USE_REAL = True
    except Exception:
        ThermodynamicGravity = None
        OttoWorkLeg = None
        _USE_REAL = False

    eps_val = epsilon.value
    T_val = temperature.value
    N_val = n_legs.value

    if _USE_REAL:
        _legs = [OttoWorkLeg(
            lorentz_violation=eps_val,
            entropy_flux=math.sin(math.pi * (_i + 1) / N_val) * 0.5,
        ) for _i in range(N_val)]
        _model = ThermodynamicGravity(temperature=T_val, work_legs=_legs)
        accel_term = _model.acceleration_term()
        measured_eps = _model.lorentz_violation_parameter()
        is_gr = _model.is_standard_gr()
        _source = "cohezion.physics"
    else:
        accel_term = sum(
            eps_val * math.sin(math.pi * (_i + 1) / N_val) * 0.5
            for _i in range(N_val)
        )
        measured_eps = eps_val
        is_gr = eps_val < 1e-9
        _source = "analytic fallback"

    _status = "✅ Standard GR (ε ≈ 0, Λ = 0)" if is_gr else f"⚡ Modified gravity (ε = {measured_eps:.3f})"
    mo.callout(
        mo.md(f"**{_status}** · Acceleration = {accel_term:.6f} · source: `{_source}`"),
        kind="success" if is_gr else "warn",
    )
    return accel_term, eps_val, is_gr, measured_eps, N_val, T_val


@app.cell
def _(go, math, mo, N_val, T_val):
    """Sweep ε from 0 to 1 and plot the acceleration-term curve."""
    _eps_range = [_i / 100 for _i in range(101)]

    def _accel(e):
        return sum(
            e * math.sin(math.pi * (_i + 1) / N_val) * 0.5
            for _i in range(N_val)
        )

    _accel_vals = [_accel(_e) for _e in _eps_range]
    _entropy_vals = [_accel(_e) / T_val for _e in _eps_range]

    fig_sweep = go.Figure()
    fig_sweep.add_trace(go.Scatter(
        x=_eps_range, y=_accel_vals,
        mode="lines", name="Acceleration term",
        line=dict(color="#4C78A8", width=2),
    ))
    fig_sweep.add_trace(go.Scatter(
        x=_eps_range, y=_entropy_vals,
        mode="lines", name=f"Entropy gain (T={T_val:.1f})",
        line=dict(color="#72B7B2", dash="dash"),
    ))
    fig_sweep.add_vline(
        x=0.0, line_dash="dot", line_color="#54A24B",
        annotation_text="Standard GR (ε=0)",
    )
    fig_sweep.update_layout(
        title=f"Late-time acceleration vs ε (N={N_val} work legs, T={T_val:.1f})",
        xaxis_title="ε (Lorentz violation)",
        yaxis_title="Acceleration proxy  Σ εᵢ·δSᵢ",
        height=400,
        legend=dict(x=0.02, y=0.98),
    )
    mo.ui.plotly(fig_sweep)
    return (fig_sweep,)


@app.cell
def _(mo):
    mo.md("## Otto Cycle Phase Portrait")
    return ()


@app.cell
def _(epsilon, go, math, mo, N_val, T_val):
    """Phase portrait of the Otto cycle in (S, δQ/T) space."""
    _eps = epsilon.value
    _phases = 100

    def _cycle_pt(phase):
        _angle = 2 * math.pi * phase
        _s_base = math.sin(_angle) * 0.5
        _q_base = math.cos(_angle) * 0.5
        _area = _eps * sum(
            math.sin(math.pi * (_i + 1) / N_val) * 0.1
            for _i in range(N_val)
        )
        return (
            _s_base + _area * math.cos(_angle * 2) / T_val,
            _q_base + _area * math.sin(_angle * 2) / T_val,
        )

    _pts = [_cycle_pt(_i / _phases) for _i in range(_phases + 1)]
    _s_pts, _q_pts = zip(*_pts)

    fig_portrait = go.Figure()
    fig_portrait.add_trace(go.Scatter(
        x=list(_s_pts), y=list(_q_pts), mode="lines",
        name=f"ε={_eps:.2f}",
        line=dict(color="#E45756", width=2),
        fill="toself" if _eps > 0.05 else None,
        fillcolor="rgba(228,87,86,0.15)",
    ))
    fig_portrait.add_trace(go.Scatter(
        x=[0], y=[0], mode="markers",
        marker=dict(color="#54A24B", size=10, symbol="x"),
        name="GR degenerate point",
    ))
    fig_portrait.update_layout(
        title="Otto Cycle Phase Portrait (S vs δQ/T)",
        xaxis_title="Entropy S",
        yaxis_title="Heat flux δQ/T",
        height=380,
    )
    mo.ui.plotly(fig_portrait)
    return (fig_portrait,)


@app.cell
def _(N_val, T_val, accel_term, epsilon, mo):
    mo.md(
        f"""
        ## Live Model State

        | Parameter | Value |
        |-----------|-------|
        | ε (Lorentz violation) | **{epsilon.value:.3f}** |
        | T (temperature) | **{T_val:.1f}** natural units |
        | N (work legs) | **{N_val}** |
        | Acceleration term | **{accel_term:.6f}** |
        | dS = δQ/T contribution | **{accel_term / T_val:.6f}** |

        > **Cosmogony link (Step 3→4):** When ε > 0, `∂_μT^μν ≠ 0` — the energy-
        > momentum tensor is no longer conserved. In the cosmogony chain this
        > corresponds to the *Fabric Differentiation* transition seeding structural
        > asymmetry from the SO(12) symmetric vacuum.
        >
        > **Cohezion harness invariant LV1:** `ThermodynamicGravity().lorentz_violation_parameter() == 0.0`
        > for the baseline GR test case.
        """
    )
    return ()


@app.cell
def _(mo):
    import os
    _default_url = os.getenv("LEMONADE_URL", "http://localhost:13305")
    gravity_query = mo.ui.text_area(
        placeholder="Ask about Lorentz violation, Otto cycles, late-time acceleration, cosmogony step 3→4...",
        label="Ask the local agent (AMD silicon, $0)",
        rows=3,
    )
    gravity_model = mo.ui.dropdown(
        ["llama3.2-1b-FLM", "Bonsai-8B-gguf", "DeepSeek-Qwen3-8B-GGUF"],
        value="llama3.2-1b-FLM",
        label="Model",
    )
    gravity_run = mo.ui.run_button(label="Ask Agent ▶")
    gravity_url = mo.ui.text(value=_default_url, label="Lemonade URL")
    mo.vstack([
        mo.md("## Live Agent — Ask About Thermodynamic Gravity"),
        mo.hstack([gravity_url, gravity_model], justify="start"),
        gravity_query,
        gravity_run,
    ])
    return gravity_model, gravity_query, gravity_run, gravity_url


@app.cell
def _(gravity_model, gravity_query, gravity_run, gravity_url, mo):
    import requests as _req

    mo.stop(not gravity_run.value, mo.md("_Configure a query above, then click **Ask Agent ▶**_"))

    def _ask(q: str, model: str, base_url: str) -> str:
        try:
            r = _req.post(
                f"{base_url.rstrip('/')}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": (
                            "You are an expert in thermodynamic gravity and the Isichei-Magueijo "
                            "2026 PRL paper (arXiv:2511.22221). Explain ε Lorentz violation, "
                            "late-time cosmic acceleration via non-degenerate Otto cycles, "
                            "and its connection to Cohezion cosmogony Step 3→4: "
                            "SO(12) symmetric vacuum → Fabric Differentiation. "
                            "Harness invariant LV1: ε=0 for standard GR baseline."
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

    _answer = _ask(gravity_query.value, gravity_model.value, gravity_url.value)
    mo.callout(mo.md(_answer), kind="info")
    return ()


if __name__ == "__main__":
    app.run()
