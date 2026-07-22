"""Reactive marimo notebook TEMPLATE — embedded local agent + interactive plot.

Copy this to start any new interactive Cohezion surface. Marimo `.py` notebooks are
git-friendly (plain source, clean diffs — just as easy for source control as a
script) yet REACTIVE + INTERACTIVE: easier to understand and steer than a straight
Python script.

    marimo edit scripts/marimo_agent_template.py    # develop (editable notebook)
    marimo run  scripts/marimo_agent_template.py    # read-only app server

Pattern (mirrors scripts/cockpit.py):
  - monitor/plot cells depend on `refresh` → auto-poll + redraw on the tick;
  - an EMBEDDED AGENT cell runs on a button click via the LOCAL fleet (:13305, $0)
    using `daemon_state.run_fleet_prompt` — never on the refresh tick;
  - a PLOT cell renders a matplotlib figure reactively (marimo renders the figure).
Replace the demo data/reader with your own; keep heavy logic in an importable module
(the notebook stays a THIN reactive UI, like cockpit.py over cohezion.cockpit).
"""

import marimo


app = marimo.App(width="medium")


@app.cell
def _imports():
    import matplotlib.pyplot as plt

    import marimo as mo

    # reuse the embedded-agent primitive (free-form prompt → local :13305, $0, fail-soft)
    from cohezion.cockpit import daemon_state as ds

    return ds, mo, plt


@app.cell
def _header(mo):
    mo.md(
        "# 🧩 <Your surface> — reactive agent notebook\n"
        "Embedded local agent + live plot. Runs on **local inference ($0)**."
    )
    return


@app.cell
def _refresh(mo):
    refresh = mo.ui.refresh(default_interval="15s", label="Auto-refresh")
    refresh
    return (refresh,)


@app.cell
def _plot(refresh, plt):
    # REPLACE the demo dict with your reactive data source (a ds.read_* reader).
    refresh  # redraw on each tick
    demo = {"alpha": 3, "beta": 5, "gamma": 2}
    fig, ax = plt.subplots(figsize=(5, 2.2))
    ax.bar(list(demo), list(demo.values()), color="#3d78d8")
    ax.set_title("Reactive plot — replace with your metric")
    fig.tight_layout()
    fig
    return


@app.cell
def _agent_controls(mo):
    agent_prompt = mo.ui.text(placeholder="ask the embedded local agent ($0)…", full_width=True)
    agent_btn = mo.ui.run_button(label="🤖 Run on local fleet")
    mo.vstack([agent_prompt, agent_btn])
    return agent_btn, agent_prompt


@app.cell
def _agent_action(mo, ds, agent_btn, agent_prompt):
    # Fires ONLY on click. Embedded RUNNING agent on the local fleet.
    mo.stop(not agent_btn.value, mo.md("_Embedded agent — type a prompt, click. Local :13305, $0._"))
    mo.stop(not agent_prompt.value.strip(), mo.md("⚠️ Prompt is empty."))
    agent_answer = ds.run_fleet_prompt(agent_prompt.value.strip())
    mo.md(f"**🤖 Local agent:**\n\n{agent_answer}")
    return


if __name__ == "__main__":
    app.run()
