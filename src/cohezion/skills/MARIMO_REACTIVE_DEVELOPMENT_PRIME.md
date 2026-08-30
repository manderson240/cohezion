# SKILL: MARIMO_REACTIVE_DEVELOPMENT_PRIME

## DOMAIN EXPERTISE
Official Marimo reactive notebook architecture, DAG dependency resolution, client-side WebAssembly (WASM/Pyodide) compilation, and zero-defect browser export.

## KEY TEXTS & CONCEPTS
- **Directed Acyclic Graph (DAG)**: Every variable in Marimo can only be defined in exactly ONE cell.
- **Topological Cell Order**: Variable declaration cells must cleanly return tuple references (e.g. `return (mo,)`) before consumer cells accept them as parameters `def _(mo):`.
- **WASM / Pyodide Purity**: For `html-wasm` exports, notebooks must not import non-whl local file paths unless bundled. Use standard Pyodide-supported libraries (`marimo`, `numpy`, `math`, `plotly`, `altair`).
- **Interactive UI Elements**: UI components (`mo.ui.slider`, `mo.ui.dropdown`) pass reactive `.value` attributes across the reactive graph without manual listeners.

## INSTRUCTION
1. Define import cells first, explicitly returning `mo`:
```python
@app.cell
def _():
    import marimo as mo
    return (mo,)
```
2. Build UI controls in intermediate cells:
```python
@app.cell
def _(mo):
    slider = mo.ui.slider(start=0, stop=100, value=50)
    return (slider,)
```
3. Consume reactive state in downstream visualization cells:
```python
@app.cell
def _(mo, slider):
    mo.md(f"Current Value: {slider.value}")
    return
```
4. Verify execution locally with `python3 notebook.py` before exporting to WASM with `marimo export html-wasm <file> -o <out.html> -f`.

## VERSION
v1.0

## SEE ALSO
- PHOENIX_REBIRTH_REPRODUCTION_PRIME
- SPINNING_PLATES_PROTOCOL_PRIME
