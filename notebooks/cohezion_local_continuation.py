# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pydantic-ai",
#     "marimo",
#     "httpx==0.28.1",
#     "duckdb==1.5.4",
#     "sqlglot==30.12.0",
#     "polars[pyarrow]==1.42.1",
#     "altair==6.2.2",
#     "vegafusion==2.0.3",
#     "vl-convert-python==1.9.0.post1",
#     "ruff==0.15.20",
#     "openai==2.44.0",
#     "mcp>=1",
#     "pydantic>=2",
#     "pytest==9.1.1",
#     "python-lsp-server==1.14.0",
#     "websockets==16.0",
#     "python-lsp-ruff==2.3.1",
#     "nbformat==5.10.4",
# ]
# ///
"""Cohezion — Local Continuation Runner (marimo reactive notebook).

PURPOSE: keep the compound-engineering work going on $0 LOCAL silicon (the lemonade :13305
OmniRouter) with NO Claude Code in the loop — for when Claude weekly availability runs out.
This embeds the "quarter-on-a-string" loop: a Dev lane (local generate) + a QA lane (local
judge — "the knot") + a running token/quarters tally. Everything runs on the local fleet.

RUN:  cd ~/dev/cohezion && uvx marimo edit notebooks/cohezion_local_continuation.py
      (uvx runs marimo without installing it; or `uvx marimo run ...` for app mode).
      Requires lemonade serving on :13305
      (`lemond --port 13305 &` if down). Zero cloud, zero API keys.
"""

import marimo

__generated_with = "0.23.11"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import httpx
    import time

    LEMONADE = "http://localhost:13305/api/v1/chat/completions"  # OpenAI-compatible, local, $0
    return LEMONADE, httpx, mo, time


@app.cell
def _(mo):
    mo.md("""
    # Cohezion — Local Continuation Runner
    **$0 local inference (lemonade :13305). No Claude required.** This is the
    quarter-on-a-string loop made standalone: Dev generates, QA jprint('local AI works')
    print('local AI works')
    print('local AI works')
    print('local AI works')
    udges (the *knot*),
    you keep the quarter. Edit the task below; cells re-run reactively.
    """)
    return


@app.cell
def _(LEMONADE, httpx, time):
    # ---- the local fleet call (the only model<->world interface) -------------------
    LEDGER = {"local_tokens": 0, "calls": 0}

    def chat(prompt: str, model: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
        """One local inference call on :13305. Tallies tokens (all local = $0)."""
        t0 = time.time()
        r = httpx.post(
            LEMONADE,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=180,
        )
        r.raise_for_status()
        d = r.json()
        out = d["choices"][0]["message"]["content"]
        LEDGER["local_tokens"] += int(d.get("usage", {}).get("total_tokens", len(out) // 4))
        LEDGER["calls"] += 1
        return out, round(time.time() - t0, 1)

    def judge(task: str, output: str, model: str) -> str:
        """QA lane — the knot. Grades Dev output PASS/FAIL against the task (local, $0)."""
        v, _ = chat(
            "You are a strict QA judge. Grade whether the OUTPUT correctly and completely "
            f"satisfies the TASK.\nTASK:\n{task}\n\nOUTPUT:\n{output}\n\n"
            "Reply with exactly one line: 'PASS' or 'FAIL: <one-sentence reason>'.",
            model=model,
            max_tokens=120,
            temperature=0.0,
        )
        return v.strip()

    return LEDGER, chat, judge


@app.cell
def _(mo):
    # Fleet models on :13305 (curl http://localhost:13305/api/v1/models to refresh).
    dev_model = mo.ui.dropdown(
        ["Gemma-4-26B-A4B-it-GGUF", "DeepSeek-Qwen3-8B-GGUF", "Bonsai-8B-gguf", "Bonsai-4B-gguf"],
        value="Gemma-4-26B-A4B-it-GGUF",
        label="Dev model (generate)",
    )
    qa_model = mo.ui.dropdown(
        ["Gemma-4-26B-A4B-it-GGUF", "DeepSeek-Qwen3-8B-GGUF", "Bonsai-8B-gguf"],
        value="Gemma-4-26B-A4B-it-GGUF",
        label="QA model (judge — keep distinct lane)",
    )
    task = mo.ui.text_area(
        label="Task / intent",
        value="Write a Python function that returns the nth Fibonacci number, with a docstring.",
        rows=4,
        full_width=True,
    )
    run = mo.ui.run_button(label="Run Dev → QA (local, $0)")
    mo.vstack([task, mo.hstack([dev_model, qa_model]), run])
    return dev_model, qa_model, run, task


@app.cell
def _(chat, dev_model, judge, mo, qa_model, run, task):
    # ---- the loop: Dev generate -> QA judge (the knot) ----------------------------
    mo.stop(not run.value, mo.md("*Press **Run** to generate + judge on local inference.*"))
    output, dev_secs = chat(task.value, model=dev_model.value)
    verdict = judge(task.value, output, model=qa_model.value)
    passed = verdict.upper().startswith("PASS")
    mo.md(
        f"### {'✅ PASS' if passed else '❌ ' + verdict}\n"
        f"*Dev: {dev_model.value} ({dev_secs}s) · QA: {qa_model.value} · $0 local*\n\n"
        f"---\n```\n{output}\n```"
    )
    return


app._unparsable_cell(
    r"""
    works')
    """,
    name="_"
)


@app.cell
def _():
    return


@app.cell
def _(LEDGER, mo):
    # ---- the ledger: every token here is local ($0). The quarter, kept. -----------
    saved = LEDGER["local_tokens"] * ((0.000003 + 0.000015) / 2)  # vs blended cloud rate
    mo.callout(
        mo.md(
            f"**Quarter-on-a-String ledger** — {LEDGER['calls']} local calls, "
            f"{LEDGER['local_tokens']:,} local tokens, **~${saved:.4f} cloud cost avoided**. "
            f"All $0 local."
        ),
        kind="success",
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## How to continue the work (without Claude)
    The repo is `~/dev/cohezion`. Key landed pieces (all cross-verified this session):
    - **qa_gate** (`src/cohezion/compound/qa_gate.py`) — risk-weighted 4-state gate; the QA *knot*.
    - **TokenLedger** (`src/cohezion/compound/token_ledger.py`) — proves local-vs-cloud spend.
    - **Cognitive-profile harness** (`src/cohezion/eval/cognitive_profile.py`, once built) —
      the AGI-framework scorecard: `uv run python scripts/eval/run_cognitive_profile.py`.
    - **Local loop**: `make_local_execute_fn` → `build_triune_omni_orchestrator` (:13305).
    - **Protocol** + **AGI gap-map** + all research: `~/vaults/cohezion-vault/reports/`.

    **To drive a real build→verify→refine cycle here:** point the Dev cell at a task, read the
    QA verdict, edit, re-run — all $0. For the autonomous loop, run
    `python ~/cohezion-labs/compound_daemon.py` (local) or the LoopCoordinator. The AGI campaign
    tasks (G0 harness → G3/G5/G7/G9/G10 axes) live in the vault gap-map; each is a bounded,
    local-inference-addressable build.
    """)
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Continue Development — Local Inference (no Claude needed)

    **The fleet** (lemonade :13305, all $0):
    `curl localhost:13305/api/v1/models` — llama3.2-1b-FLM (NPU/fast), Gemma-4-26B-A4B-it-GGUF (reasoning),
    DeepSeek-Qwen3-8B-GGUF, Bonsai-8B-gguf. If down: `lemond --port 13305 &`.

    **Tools** (in `~/dev/cohezion/scripts/`, all $0 local):
    - `uv run python scripts/gaia_orchestrator.py "<task>"` — BMAD Dev→QA loop; escalates to
      `~/.cohezion/advice_queue.jsonl` when stuck.
    - `uv run python scripts/local_research.py <url> [topic]` — research/audit any URL → vault report.
    - `uv run python scripts/storage_manager.py` — HF cache index (~100 GB reclaimable; manifest at
      `~/.cohezion/storage_manifest.json`).
    - This notebook — interactive Dev→QA runner + marimo AI assist.

    **marimo AI assist setup** (so "Generate with AI" calls lemonade):
    - install `pydantic_ai`
    - `~/.config/marimo/marimo.toml`: `[ai.custom_providers.lemonade]` `base_url = "http://localhost:13305/v1"`;
      models = `lemonade/<model>`. (lemonade is its OWN provider; `[ai.ollama]` is left free for real Ollama.)

    **Next steps toward the AGI-framework goal:**
    1. Re-run the scorecard: `uv run python scripts/eval/cognitive_profile_cli.py` (11 MET / 1 PARTIAL / 3 BEYOND_REACH).
    2. Close engineering-addressable axes #10–15 (gap-map in `~/vaults/cohezion-vault/reports/`) via the
       orchestrator, one at a time, Dev→QA cross-verified (never self-signoff).
    3. Close the orchestration leak: TokenLedger `local_fraction = 0.025` — point the orchestrator at real
       build tasks so orchestration moves onto local silicon; watch it climb.
    4. BEYOND_REACH (native vision/audio, broad knowledge, frontier Gf) = substrate-limited — measure, never fake.

    **Escalate to Claude** (budget resets Fri 5pm): paste `~/.cohezion/advice_queue.jsonl` + the latest
    scorecard. Full handoff: `~/vaults/cohezion-vault/reports/SESSION-HANDOFF-2026-06-30.md`.
    """)
    return


if __name__ == "__main__":
    app.run()
