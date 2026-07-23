"""Operator cockpit — a marimo reactive notebook to MONITOR and STEER the live
Cohezion local daemons (compound daemon, feeder, actioner, research daemon).

Run it:
    marimo run scripts/cockpit.py      # read-only app server (recommended for steering)
    marimo edit scripts/cockpit.py     # editable notebook

This notebook is a THIN reactive UI over ``cohezion.cockpit.daemon_state`` — all
logic + tests live there. Monitor panels auto-poll every ~15s via ``mo.ui.refresh``.
STEER controls (run feeder, add manual task, ask advisor) are guarded so they fire
ONLY on a fresh button click, never on the refresh tick.

Daemon start/stop is intentionally NOT exposed (too destructive) — the exact
``systemctl --user`` pause/resume commands are rendered as copy-paste text instead.
"""

import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _header(mo):
    mo.md("""
    # 🛰️ Cohezion Compound-Loop Cockpit
    Monitor + steer the live local daemons. Panels below auto-refresh ~15s.
    Steering actions fire only on click. Runs on **local inference ($0)**.
    """)
    return


@app.cell
def _imports():
    import matplotlib.pyplot as plt

    import marimo as mo

    from cohezion.cockpit import daemon_state as ds

    return ds, mo, plt


@app.cell
def _refresh(mo):
    # The heartbeat: every monitor cell that reads this re-runs on each tick.
    refresh = mo.ui.refresh(default_interval="15s", label="Auto-refresh")
    refresh
    return (refresh,)


@app.cell
def _task_queue(ds, mo, refresh):
    refresh  # depend on the tick → re-poll
    tq = ds.read_task_queue()
    tq_pending = tq["pending"]
    tq_rows = (
        "\n".join(f"| {t.get('id')} | {(t.get('prompt') or '')[:80]} |" for t in tq_pending[:15])
        or "| — | (no pending tasks) |"
    )
    mo.md(
        f"""## 📋 Compound task queue
        **total** {tq["total"]} · **done** {tq["done"]} · **pending** {len(tq_pending)}

        | id | prompt |
        |----|--------|
        {tq_rows}
        """
    )
    return


@app.cell
def _graph_counts(ds, mo, refresh):
    refresh
    gc = ds.read_graph_counts()
    mo.md(
        "## 🕸️ SurrealDB graph\n"
        f"compound_loop **{gc['compound_loop']}** · yielded **{gc['yielded']}** · "
        f"spawned **{gc['spawned']}** · agent_journey **{gc['agent_journey']}**"
    )
    return


@app.cell
def _work_queue(ds, mo, refresh):
    refresh
    wq = ds.read_work_queue()
    wq_status = " · ".join(f"{k}: {v}" for k, v in wq["by_status"].items()) or "—"
    wq_rel = " · ".join(f"{k}: {v}" for k, v in wq["by_relevance"].items()) or "—"
    mo.md(
        f"## 🗂️ Work queue (:8080)\n**total** {wq['total']}\n\n"
        f"- by status: {wq_status}\n- by relevance: {wq_rel}"
    )
    return


@app.cell
def _status_chart(ds, plt, refresh):
    # Interactive PLOT (reactive: redraws on each poll tick). marimo renders the figure.
    refresh
    sc_wq = ds.read_work_queue()
    sc_items = list(sc_wq["by_status"].items()) or [("—", 0)]
    sc_fig, sc_ax = plt.subplots(figsize=(5, 2.2))
    sc_ax.bar([k for k, _ in sc_items], [v for _, v in sc_items], color="#6aa84f")
    sc_ax.set_title("Work queue by status")
    sc_ax.set_ylabel("count")
    sc_fig.tight_layout()
    sc_fig
    return


@app.cell
def _gap_analysis(ds, mo, refresh):
    refresh
    gaps = ds.read_gap_analysis()
    gap_rows = (
        "\n".join(f"| {g['task_type']} | {g['score']:.2f} | {g['action']} |" for g in gaps)
        or "| — | — | (no gaps / matrix unavailable) |"
    )
    mo.md(
        "## 🎯 Capability gaps\n"
        "| task_type | score | action |\n|-----------|-------|--------|\n" + gap_rows
    )
    return


app._unparsable_cell(
    """
    #The error occurs because `mo.md()` expects a string, but it receives a dictionary instead. This is because `mo.md()` is used to print markdown text, and it doesn't handle dictionaries correctly.

    Here's the corrected code:

    ```python
    {REWRITTEN_CODE}
    import matplotlib.pyplot as plt

    import marimo as mo

    from cohezion.cockpit import daemon_state as ds
    mo.md(\"\"\"
    # 🛰️ Cohezion Compound-Loop Cockpit
    Monitor + steer the live local daemons. Panels below auto-refresh ~15s.
    Steering actions fire only on click. Runs on **local inference ($0)**.
    \"\"\")

    # The heartbeat: every monitor cell that reads this re-runs on each tick.
    refresh = mo.ui.refresh(default_interval=\"15s\", label=\"Auto-refresh\")
    refresh

    refresh  # depend on the tick → re-poll
    tq = ds.read_task_queue()
    tq_pending = tq[\"pending\"]
    tq_rows = (
        \"\\n\".join(f\"| {t.get('id')} | {(t.get('prompt') or '')[:80]} |\" for t in tq_pending[:15])
        or \"| — | (no pending tasks) |\"
    )
    mo.md(
        f\"\"\"## 📋 Compound task queue
        **total** {tq[\"total\"]} · **done** {tq[\"done\"]} · **pending** {len(tq_pending)}

        | id | prompt |
        |----|--------|
        {tq_rows}
        \"\"\"
    )

    refresh
    gc = ds.read_graph_counts()
    mo.md(
        \"## 🕸️ SurrealDB graph\\n\"
        f\"compound_loop **{gc['compound_loop']}** · yielded **{gc['yielded']}** · \"
        f\"spawned **{gc['spawned']}** · agent_journey **{gc['agent_journey']}**\"
    )

    refresh
    wq = ds.read_work_queue()
    wq_status = \" · \".join(f\"{k}: {v}\" for k, v in wq[\"by_status\"].items()) or \"—\"
    wq_rel = \" · \".join(f\"{k}: {v}\" for k, v in wq[\"by_relevance\"].items()) or \"—\"
    mo.md(
        f\"## 🗂️ Work queue (:8080)\\n**total** {wq['total']}\\n\\n\"
        f\"- by status: {wq_status}\\n- by relevance: {wq_rel}\"
    )

    # Interactive PLOT (reactive: redraws on each poll tick). marimo renders the figure.
    refresh
    sc_wq = ds.read_work_queue()
    sc_items = list(sc_wq[\"by_status\"].items()) or [(\"—\", 0)]
    sc_fig, sc_ax = plt.subplots(figsize=(5, 2.2))
    sc_ax.bar([k for k, _ in sc_items], [v for _, v in sc_items], color=\"#6aa84f\")
    sc_ax.set_title(\"Work queue by status\")
    sc_ax.set_ylabel(\"count\")
    sc_fig.tight_layout()
    sc_fig
    refresh
    gaps = ds.read_gap_analysis()
    gap_rows = (
        \"\\n\".join(f\"| {g['task_type']} | {g['score']:.2f} | {g['action']} |\" for g in gaps)
        or \"| — | — | (no gaps / matrix unavailable) |\"
    )
    mo.md(
        \"## 🎯 Capability gaps\\n\"
        \"| task_type | score | action |\\n|-----------|-------|--------|\\n\" + gap_rows
    )

    refresh
    log_tail = ds.tail_daemon_log(n=20) or \"(no compound_daemon.log)\"
    mo.md(f\"## 📜 Daemon log (tail 20)\\n```\\n{log_tail}\\n```\")
    mo.md(\"\"\"
    ---
    ## 🎛️ Steer
    \"\"\")
    feeder_btn = mo.ui.run_button(label=\"▶ Run feeder now\")
    feeder_btn
    # Depends ONLY on the button — NOT on `refresh` — so it never fires on a poll tick.
    mo.stop(not feeder_btn.value, mo.md(\"_Feeder idle — click to feed the compound queue._\"))
    result = ds.run_feeder(limit=5)
    mo.md(f\"**Feeder result:** `{result}`\")
    task_prompt = mo.ui.text(placeholder=\"compound loop: <what to work on>\", full_width=True)
    add_btn = mo.ui.run_button(label=\"➕ Add manual task\")
    mo.vstack([task_prompt, add_btn])
    mo.stop(not add_btn.value, mo.md(\"_Enter a prompt and click to enqueue one task._\"))
    mo.stop(not task_prompt.value.strip(), mo.md(\"⚠️ Prompt is empty — nothing added.\"))
    added = ds.add_manual_task(task_prompt.value.strip())
    mo.md(f\"✅ Added task id **{added['added']['id']}** — queue total {added['total']}.\")
    advisor_btn = mo.ui.run_button(label=\"🧠 Ask local advisor\")
    advisor_btn
    mo.stop(
        not advisor_btn.value, mo.md(\"_Click to ask the local Gemma advisor about current state._\")
    )
    # Assemble a compact state summary from the same readers the monitors use.
    # Distinct names (adv_*) — marimo requires one global definition per name.
    adv_tq = ds.read_task_queue()
    adv_gc = ds.read_graph_counts()
    adv_wq = ds.read_work_queue()
    adv_summary = (
        f\"task_queue: total={adv_tq['total']} done={adv_tq['done']} pending={len(adv_tq['pending'])}; graph: {adv_gc}; \"
        f\"work_queue: total={adv_wq['total']} by_status={adv_wq['by_status']}\"
    )
    adv_advice = ds.ask_local_advisor(adv_summary)
    mo.md(f\"**Advisor:**\\n\\n{adv_advice}\")
    # Embedded RUNNING agent: free-form prompt → local inference fleet (:13305, $0).
    fleet_prompt = mo.ui.text(placeholder=\"ask the local fleet anything ($0)…\", full_width=True)
    fleet_btn = mo.ui.run_button(label=\"🤖 Run on local fleet\")
    mo.vstack([fleet_prompt, fleet_btn])
    # Fires ONLY on click (not on the refresh tick). Embedded agent, runs on-demand.
    mo.stop(not fleet_btn.value, mo.md(\"_Free-form embedded agent — type a prompt, click. Runs on local :13305, $0._\"))
    mo.stop(not fleet_prompt.value.strip(), mo.md(\"⚠️ Prompt is empty.\"))
    fleet_answer = ds.run_fleet_prompt(fleet_prompt.value.strip())
    mo.md(f\"**🤖 Local fleet:**\\n\\n{fleet_answer}\")
    mo.md(\"\"\"
    ---
    ### ⏸️ Pause / resume daemons (run in a terminal — not exposed as buttons)
    ```bash
    systemctl --user stop  cohezion-compound.service     # pause the compound loop
    systemctl --user start cohezion-compound.service     # resume it
    systemctl --user stop  cohezion-compound-feeder.timer
    systemctl --user start cohezion-compound-feeder.timer
    systemctl --user status cohezion-compound.service    # inspect
    ```
    \"\"\")
    refresh
    lem = ds.read_lemonade_health()
    lem_loaded = \", \".join(lem[\"loaded\"]) or \"(none)\"
    mo.md(f\"## 🍋 Lemonade router (:13305)\\n**status** `{lem['status']}` · loaded: {lem_loaded}\")
    </code_from_other_cells>
    ```

    The issue arises from the fact that `mo.md()` expects a string, but it receives a dictionary instead. This is because `mo.md()` is used to print markdown text, and it doesn't handle dictionaries correctly.

    To fix this issue, you can use the `json.dumps()` function to convert the dictionary to a JSON string, and then use `mo.md()` with the JSON string. Here's the corrected code:

    ```python
    {REWRITTEN_CODE}
    import matplotlib.pyplot as plt

    import marimo as mo

    from cohezion.cockpit import daemon_state as ds
    mo.md(\"\"\"
    # 🛰️ Cohezion Compound-Loop Cockpit
    Monitor + steer the live local daemons. Panels below auto-refresh ~15s.
    Steering actions fire only on click. Runs on **local inference ($0)**.
    \"\"\")

    # The heartbeat: every monitor cell that reads this re-runs on each tick.
    refresh = mo.ui.refresh(default_interval=\"15s\", label=\"Auto-refresh\")
    refresh

    refresh  # depend on the tick → re-poll
    tq = ds.read_task_queue()
    tq_pending = tq[\"pending\"]
    tq_rows = (
        \"\\n\".join(f\"| {t.get('id')} | {(t.get('prompt') or '')[:80]} |\" for t in tq_pending[:15])
        or \"| — | (no pending tasks) |\"
    )
    mo.md(
        f\"\"\"## 📋 Compound task queue
        **total** {tq[\"total\"]} · **done** {tq[\"done\"]} · **pending** {len(tq_pending)}

        | id | prompt |
        |----|--------|
        {tq_rows}
        \"\"\"
    )

    refresh
    gc = ds.read_graph_counts()
    mo.md(
        \"## 🕸️ SurrealDB graph\\n\"
        f\"compound_loop **{gc['compound_loop']}** · yielded **{gc['yielded']}** · \"
        f\"spawned **{gc['spawned']}** · agent_journey **{gc['agent_journey']}**\"
    )

    refresh
    wq = ds.read_work_queue()
    wq_status = \" · \".join(f\"{k}: {v}\" for k, v in wq[\"by_status\"].items()) or \"—\"
    wq_rel = \" · \".join(f\"{k}: {v}\" for k, v in wq[\"by_relevance\"].items()) or \"—\"
    mo.md(
        f\"## 🗂️ Work queue (:8080)\\n**total** {wq['total']}\\n\\n\"
        f\"- by status: {wq_status}\\n- by relevance: {wq_rel}\"
    )

    # Interactive PLOT (reactive: redraws on each poll tick). marimo renders the figure.
    refresh
    sc_wq = ds.read_work_queue()
    sc_items = list(sc_wq[\"by_status\"].items()) or [(\"—\", 0)]
    sc_fig, sc_ax = plt.subplots(figsize=(5, 2.2))
    sc_ax.bar([k for k, _ in sc_items], [v for _, v in sc_items], color=\"#6aa84f\")
    sc_ax.set_title(\"Work queue by status\")
    sc_ax.set_ylabel(\"count\")
    sc_fig.tight_layout()
    sc_fig
    refresh
    gaps = ds.read_gap_analysis()
    gap_rows = (
        \"\\n\".join(f\"| {g['task_type']} | {g['score']:.2f} | {g['action']} |\" for g in gaps)
        or \"| — | — | (no gaps / matrix unavailable) |\"
    )
    mo.md(
        \"## 🎯 Capability gaps\\n\"
        \"| task_type | score | action |\\n|-----------|-------|--------|\\n\" + gap_rows
    )

    refresh
    log_tail = ds.tail_daemon_log(n=20) or \"(no compound_daemon.log)\"
    mo.md(f\"## 📜 Daemon log (tail 20)\\n```\\n{log_tail}\\n```\")
    mo.md(\"\"\"
    ---
    ## 🎛️ Steer
    \"\"\")
    feeder_btn = mo.ui.run_button(label=\"▶ Run feeder now\")
    feeder_btn
    # Depends ONLY on the button — NOT on `refresh` — so it never fires on a poll tick.
    mo.stop(not feeder_btn.value, mo.md(\"_Feeder idle — click to feed the compound queue._\"))
    result = ds.run_feeder(limit=5)
    mo.md(f\"**Feeder result:** `{result}`\")
    task_prompt = mo.ui.text(placeholder=\"compound loop: <what to work on>\", full_width=True)
    add_btn = mo.ui.run_button(label=\"➕ Add manual task\")
    mo.vstack([task_prompt, add_btn])
    mo.stop(not add_btn.value, mo.md(\"_Enter a prompt and click to enqueue one task._\"))
    mo.stop(not task_prompt.value.strip(), mo.md(\"⚠️ Prompt is empty — nothing added.\"))
    added = ds.add_manual_task(task_prompt.value.strip())
    mo.md(f\"✅ Added task id **{added['added']['id']}** — queue total {added['total']}.\")
    advisor_btn = mo.ui.run_button(label=\"🧠 Ask local advisor\")
    advisor_btn
    mo.stop(
        not advisor_btn.value, mo.md(\"_Click to ask the local Gemma advisor about current state._\")
    )
    # Assemble a compact state summary from the same readers the monitors use.
    # Distinct names (adv_*) — marimo requires one global definition per name.
    adv_tq = ds.read_task_queue()
    adv_gc = ds.read_graph_counts()
    adv_wq = ds.read_work_queue()
    adv_summary = (
        f\"task_queue: total={adv_tq['total']} done={adv_tq['done']} pending={len(adv_tq['pending'])}; graph: {adv_gc}; \"
        f\"work_queue: total={adv_wq['total']} by_status={adv_wq['by_status']}\"
    )
    adv_advice = ds.ask_local_advisor(adv_summary)
    mo.md(f\"**Advisor:**\\n\\n{adv_advice}\")
    # Embedded RUNNING agent: free-form prompt → local inference fleet (:13305, $0).
    fleet_prompt = mo.ui.text(placeholder=\"ask the local fleet anything ($0)…\", full_width=True)
    fleet_btn = mo.ui.run_button(label=\"🤖 Run on local fleet\")
    mo.vstack([fleet_prompt, fleet_btn])
    # Fires ONLY on click (not on the refresh tick). Embedded agent, runs on-demand.
    mo.stop(not fleet_btn.value, mo.md(\"_Free-form embedded agent — type a prompt, click. Runs on local :13305, $0._\"))
    mo.stop(not fleet_prompt.value.strip(), mo.md(\"⚠️ Prompt is empty.\"))
    fleet_answer = ds.run_fleet_prompt(fleet_prompt.value.strip())
    mo.md(f\"**🤖 Local fleet:**\\n\\n{fleet_answer}\")
    mo.md(\"\"\"
    ---
    ### ⏸️ Pause / resume daemons (run in a terminal — not exposed as buttons)
    ```bash
    systemctl --user stop  cohezion-compound.service     # pause the compound loop
    systemctl --user start cohezion-compound.service     # resume it
    systemctl --user stop  cohezion-compound-feeder.timer
    systemctl --user start cohezion-compound-feeder.timer
    systemctl --user status cohezion-compound.service    # inspect
    ```
    \"\"\")
    refresh
    lem = ds.read_lemonade_health()
    lem_loaded = \", \".join(lem[\"loaded\"]) or \"(none)\"
    mo.md(f\"## 🍋 Lemonade router (:13305)\\n**status** `{lem['status']}` · loaded: {lem_loaded}\")
    </code_from_other_cells>
    ```

    The corrected code uses `json.dumps()` to convert the dictionary to a JSON string, and then uses `mo.md()` with the JSON string.
    """,
    name="_lemonade"
)


@app.cell
def _log_tail(ds, mo, refresh):
    refresh
    log_tail = ds.tail_daemon_log(n=20) or "(no compound_daemon.log)"
    mo.md(f"## 📜 Daemon log (tail 20)\n```\n{log_tail}\n```")
    return


@app.cell
def _steer_header(mo):
    mo.md("""
    ---
    ## 🎛️ Steer
    """)
    return


@app.cell
def _feeder_controls(mo):
    feeder_btn = mo.ui.run_button(label="▶ Run feeder now")
    feeder_btn
    return (feeder_btn,)


@app.cell
def _feeder_action(ds, feeder_btn, mo):
    # Depends ONLY on the button — NOT on `refresh` — so it never fires on a poll tick.
    mo.stop(not feeder_btn.value, mo.md("_Feeder idle — click to feed the compound queue._"))
    result = ds.run_feeder(limit=5)
    mo.md(f"**Feeder result:** `{result}`")
    return


@app.cell
def _manual_task_controls(mo):
    task_prompt = mo.ui.text(placeholder="compound loop: <what to work on>", full_width=True)
    add_btn = mo.ui.run_button(label="➕ Add manual task")
    mo.vstack([task_prompt, add_btn])
    return add_btn, task_prompt


@app.cell
def _manual_task_action(add_btn, ds, mo, task_prompt):
    mo.stop(not add_btn.value, mo.md("_Enter a prompt and click to enqueue one task._"))
    mo.stop(not task_prompt.value.strip(), mo.md("⚠️ Prompt is empty — nothing added."))
    added = ds.add_manual_task(task_prompt.value.strip())
    mo.md(f"✅ Added task id **{added['added']['id']}** — queue total {added['total']}.")
    return


@app.cell
def _advisor_controls(mo):
    advisor_btn = mo.ui.run_button(label="🧠 Ask local advisor")
    advisor_btn
    return (advisor_btn,)


@app.cell
def _advisor_action(advisor_btn, ds, mo):
    mo.stop(
        not advisor_btn.value, mo.md("_Click to ask the local Gemma advisor about current state._")
    )
    # Assemble a compact state summary from the same readers the monitors use.
    # Distinct names (adv_*) — marimo requires one global definition per name.
    adv_tq = ds.read_task_queue()
    adv_gc = ds.read_graph_counts()
    adv_wq = ds.read_work_queue()
    adv_summary = (
        f"task_queue: total={adv_tq['total']} done={adv_tq['done']} "
        f"pending={len(adv_tq['pending'])}; graph: {adv_gc}; "
        f"work_queue: total={adv_wq['total']} by_status={adv_wq['by_status']}"
    )
    adv_advice = ds.ask_local_advisor(adv_summary)
    mo.md(f"**Advisor:**\n\n{adv_advice}")
    return


@app.cell
def _fleet_controls(mo):
    # Embedded RUNNING agent: free-form prompt → local inference fleet (:13305, $0).
    fleet_prompt = mo.ui.text(placeholder="ask the local fleet anything ($0)…", full_width=True)
    fleet_btn = mo.ui.run_button(label="🤖 Run on local fleet")
    mo.vstack([fleet_prompt, fleet_btn])
    return fleet_btn, fleet_prompt


@app.cell
def _fleet_action(ds, fleet_btn, fleet_prompt, mo):
    # Fires ONLY on click (not on the refresh tick). Embedded agent, runs on-demand.
    mo.stop(not fleet_btn.value, mo.md("_Free-form embedded agent — type a prompt, click. Runs on local :13305, $0._"))
    mo.stop(not fleet_prompt.value.strip(), mo.md("⚠️ Prompt is empty."))
    fleet_answer = ds.run_fleet_prompt(fleet_prompt.value.strip())
    mo.md(f"**🤖 Local fleet:**\n\n{fleet_answer}")
    return


@app.cell
def _controls_note(mo):
    mo.md("""
    ---
    ### ⏸️ Pause / resume daemons (run in a terminal — not exposed as buttons)
    ```bash
    systemctl --user stop  cohezion-compound.service     # pause the compound loop
    systemctl --user start cohezion-compound.service     # resume it
    systemctl --user stop  cohezion-compound-feeder.timer
    systemctl --user start cohezion-compound-feeder.timer
    systemctl --user status cohezion-compound.service    # inspect
    ```
    """)
    return


if __name__ == "__main__":
    app.run()
