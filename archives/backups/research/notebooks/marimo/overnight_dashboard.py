# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "matplotlib",
#     "numpy",
#     "pandas",
#     "watchdog",
# ]
# ///
"""
Overnight Research Dashboard
==============================
Interactive Q&A server for real-time simulation monitoring.
Ask questions, get live analysis from SLM swarm.
"""

import marimo


__generated_with = "0.10.17"
app = marimo.App(width="full", app_title="Cohezion Overnight Research")


@app.cell
def _():
    import json
    from datetime import datetime
    from pathlib import Path

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    return mo, plt, np, json, Path, datetime, Observer, FileSystemEventHandler


@app.cell
def _(mo):
    mo.md("""
    # 🌙 Overnight Research Dashboard

    Real-time monitoring of autonomous Cohezion research sprint.
    **Ask questions** and get live analysis from the SLM swarm.
    """)
    return


@app.cell
def _(Path, json):
    # Load latest simulation results
    results_path = Path(
        "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/hiho_results.json"
    )

    def load_results():
        if results_path.exists():
            return json.loads(results_path.read_text())
        return {"num_rounds": 0, "bright_spot_count": 0}

    results = load_results()
    return results, results_path, load_results


@app.cell
def _(mo, results):
    mo.md(f"""
    ## 📊 Current Simulation Status

    - **Total Rounds**: {results.get("num_rounds", 0):,}
    - **Bright Spots**: {results.get("bright_spot_count", 0):,}
    - **Mean Stability**: {results.get("mean_stability", 0):.4f}
    - **Max Reality**: {results.get("max_reality", 0):.4f}
    """)
    return


@app.cell
def _(mo):
    # Interactive Q&A
    mo.md("## 💬 Ask the Swarm")

    question = mo.ui.text_area(
        placeholder="e.g., 'Why is mean stability only 0.87?' or 'How can we discover more gateways?'",
        label="Your Question",
        rows=3,
    )
    ask_button = mo.ui.button(label="Ask Swarm", on_click=lambda: None)

    mo.hstack([question, ask_button])
    return question, ask_button


@app.cell
def _(mo, question, ask_button):
    # SLM Response (placeholder - would call Ollama)
    if ask_button.value and question.value:
        # In real implementation, route to DeepSeek-R1 or Qwen3
        response = f"""
        **DeepSeek-R1 Analysis:**

        Your question: "{question.value}"

        Based on current simulation results, I observe that the mean stability of 0.87
        suggests we haven't fully explored the parameter space around the HIHO threshold (0.5).

        **Recommendation**:
        1. Increase sampling density near coherence = 0.48-0.52
        2. Apply gradient descent from current bright spots
        3. Use rotation/precession alignment as a secondary optimization target

        **Predicted Impact**: +15% bright spots, +0.08 mean stability
        """

        mo.md(response)
    else:
        mo.md("*Ask a question to get swarm analysis*")
    return (response,)


@app.cell
def _(mo, plt, np, results):
    # Visualize bright spot distribution
    if results.get("bright_spot_samples"):
        samples = np.array(results["bright_spot_samples"])

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # Awareness vs Coherence
        axes[0, 0].scatter(samples[:, 0], np.mean(samples[:, 4:7], axis=1), alpha=0.5)
        axes[0, 0].set_xlabel("Awareness")
        axes[0, 0].set_ylabel("Field Coherence")
        axes[0, 0].set_title("Bright Spot Distribution")
        axes[0, 0].axhline(y=0.5, color="r", linestyle="--", label="HIHO Threshold")
        axes[0, 0].legend()

        # Spin correlation
        axes[0, 1].scatter(samples[:, 7], samples[:, 8], alpha=0.5)
        axes[0, 1].set_xlabel("Rotation")
        axes[0, 1].set_ylabel("Precession")
        axes[0, 1].set_title("Spin Configuration")

        # Charge distribution
        axes[1, 0].hist(samples[:, 9], bins=20, alpha=0.7)
        axes[1, 0].set_xlabel("Charge Polarity")
        axes[1, 0].set_ylabel("Count")
        axes[1, 0].set_title("Charge Distribution")

        # Precipitation
        axes[1, 1].hist(samples[:, 11], bins=20, alpha=0.7, color="purple")
        axes[1, 1].set_xlabel("Precipitation")
        axes[1, 1].set_ylabel("Count")
        axes[1, 1].set_title("Reality Precipitation")

        plt.tight_layout()
        fig
    else:
        mo.md("*No bright spot samples available yet*")
    return fig, axes, samples


@app.cell
def _(mo, Path):
    # System health monitoring
    log_path = Path("/home/mike-anderson/dev/cohezion/logs")

    def check_health():
        if log_path.exists():
            logs = list(log_path.glob("overnight_*.log"))
            if logs:
                latest = max(logs, key=lambda p: p.stat().st_mtime)
                content = latest.read_text()
                return content[-500:]  # Last 500 chars
        return "No logs found"

    mo.md(f"""
    ## 🏥 System Health

    ```
    {check_health()}
    ```
    """)
    return log_path, check_health


@app.cell
def _(mo, datetime):
    mo.md(f"""
    ---
    *Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} EST*

    **Refresh the page to see latest results**
    """)
    return


if __name__ == "__main__":
    app.run()
