# SKILL: MARIMO_NOTEBOOKS_PRIME

## DOMAIN EXPERTISE
You are a specialist in **Marimo reactive Python notebooks**. You understand reactive execution, UI widgets, deployment, and integration with Quarto for living research documents.

## KEY TEXTS & CONCEPTS
- **Reactive Execution:** Cells auto-update based on dependency DAG
- **Pure Python Storage:** Notebooks stored as `.py` files (Git-friendly)
- **mo.ui Elements:** Sliders, dropdowns, tables, buttons
- **Marimo Islands:** Embed reactive content in Quarto documents
- **Deployment:** Run notebooks as web applications

## INSTALLATION
```bash
# Install Marimo
pip install marimo

# Create new notebook
marimo edit my_notebook.py

# Run as app
marimo run my_notebook.py

# Add Quarto extension
quarto add marimo-team/quarto-marimo
```

## INSTRUCTION

### 1. Basic Notebook Structure
```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "pandas", "plotly"]
# ///

import marimo as mo
import pandas as pd
import plotly.express as px

# Cell 1: UI Controls
coherence_slider = mo.ui.slider(
    start=0.0, stop=1.0, value=0.7,
    label="Coherence Threshold"
)
mo.md(f"## Threshold: {coherence_slider.value}")

# Cell 2: Reactive Data Loading (auto-updates when slider changes)
@mo.cache
def load_data():
    return pd.read_json("flume_trajectories.jsonl", lines=True)

df = load_data()
filtered = df[df['coherence'] > coherence_slider.value]
mo.md(f"Showing **{len(filtered)}** of {len(df)} trajectories")

# Cell 3: Visualization (auto-updates)
fig = px.scatter(filtered, x='step', y='coherence', color='stream')
mo.ui.plotly(fig)
```

### 2. Interactive Tables
```python
# Selectable table
table = mo.ui.table(
    df,
    selection="multi",
    pagination=True,
    page_size=20
)

# React to selection
if table.value is not None:
    selected = table.value
    mo.md(f"Selected {len(selected)} rows")
```

### 3. Forms and Buttons
```python
# Form with multiple inputs
form = mo.ui.batch(
    mo.md("### Simulation Parameters"),
    stream=mo.ui.dropdown(
        options=["architect", "engineer", "biologist"],
        value="architect"
    ),
    steps=mo.ui.number(value=100, start=1, stop=1000),
    run=mo.ui.run_button()
)

if form.value["run"]:
    result = run_simulation(form.value["stream"], form.value["steps"])
    mo.md(f"Simulation complete: {result}")
```

### 4. Quarto Integration (.qmd)
```markdown
---
title: "FLUME Living Research"
format: html
filters:
  - marimo
---

## Interactive Analysis

```{.marimo}
import marimo as mo
slider = mo.ui.slider(0, 100, value=50)
mo.md(f"Value: {slider.value}")
```

This creates an interactive Quarto document with live Python.
```

### 5. Deployment as Web App
```bash
# Run with public access
marimo run notebook.py --host 0.0.0.0 --port 8080

# Export as static HTML (with interactivity)
marimo export html notebook.py > output.html

# Docker deployment
docker run -p 2718:2718 -v $(pwd)/notebooks:/app/notebooks cohezion-notebooks
```

### 6. Caching for Performance
```python
@mo.cache
def expensive_computation(param):
    """Cached function - only recomputes when param changes."""
    return heavy_calculation(param)

# Lazy evaluation
@mo.lazy
def load_large_dataset():
    return pd.read_parquet("large_file.parquet")
```

## APPLICATIONS
- **Living Research Papers:** Quarto + Marimo for interactive publications
- **Simulation Dashboards:** Real-time parameter exploration
- **Data Exploration:** Interactive filtering and visualization
- **Team Collaboration:** Git-friendly, reproducible notebooks

## VERSION
v1.0

## SEE ALSO
- INTERACTIVE_UI_PRIME.md
- 3D_RENDERING_PRIME.md
- FLUME_METHODOLOGY_PRIME.md
