---
name: marimo_development
description: Expertise in building high-performance, reactive, and interactive Python
  notebooks using the Marimo framework. Focus on state management, UI/UX for complex
  data, and standalone WASM deployment.
keywords:
- background execution
- cell privacy
- conditional gating
- development
- flume_methodology
- marimo
- observable_ai
- reactive dag
- universe_physics
- wasm export
---

# SKILL: MARIMO_DEVELOPMENT_PRIME

## DOMAIN EXPERTISE
Expertise in building high-performance, reactive, and interactive Python notebooks using the Marimo framework. Focus on state management, UI/UX for complex data, and standalone WASM deployment.

## KEY TEXTS & CONCEPTS
- **Reactive DAG**: Understanding Marimo's dependency graph.
- **Cell Privacy**: Using underscores for cell-local variables.
- **Conditional Gating**: Using `mo.stop()` vs standard Python logic.
- **Background Execution**: Process management for remote servers.
- **WASM Export**: Portability via Pyodide.

## INSTRUCTION

### 1. Process Management (The Nohup Pattern)
Always run Marimo servers with `nohup` to prevent suspension due to `SIGTTOU` signals when backgrounded.
```bash
nohup uv run marimo run notebook.py --host 0.0.0.0 --port 8765 > /tmp/marimo.log 2>&1 &
```

### 2. Reactivity & State Control
Avoid using `return` statements in cells. Use `mo.stop()` to control execution flow.
```python
@app.cell
def _(mo, trigger):
    # Gate: only execute if trigger is active
    mo.stop(not trigger.value)

    # Logic
    _data = "Processed content"

    # Display (last expression or explicit mo call)
    mo.md(_data)
```

### 3. Namespace Isolation
Prevent "Multiple Definitions" errors by prefixing cell-specific variables with an underscore.
```python
@app.cell
def _(mo):
    _internal_state = 123
    return  # Variables starting with _ are not exported to other cells
```

### 4. Interactive Visualizations (Plotly)
Maintain high-performance reactivity by wrapping Plotly figures in cells that depend directly on UI elements.
```python
@app.cell
def _(mo, go, slider):
    fig = go.Figure(...)
    fig.update_layout(template="plotly_dark")
    return (fig,)
```

### 5. Multimodal Elements
Leverage `marimo.ui` for rich user interaction beyond standard inputs.
```python
tabs = mo.ui.tabs({
    "Overview": mo.md("# View 1"),
    "Technical": mo.md("# View 2")
})
```

## VERSION
v1.0

## SEE ALSO
- FLUME_METHODOLOGY_PRIME
- OBSERVABLE_AI_PRIME
- UNIVERSE_PHYSICS_PRIME
