# GEMINI.md - Agent Configuration & Learnings

This file documents agent-discovered patterns and configuration for the Cohezion project.

## Session Learnings (2026-01-19)

### Marimo Notebooks

**Process Management:**
```bash
# ✅ Correct (stays running)
nohup uv run marimo run notebook.py --host 0.0.0.0 --port 8765 > /tmp/marimo.log 2>&1 &
```

**Cell Patterns:**
- **No `return`**: Cells are not functions; they don't support `return`.
- **Reactivity**: Use `mo.stop(not condition)` to gate conditional UI display.
- **Privacy**: Use `_variable` prefix for cell-private variables to avoid cross-cell conflicts.
- **WASM Export**: `marimo export html-wasm script.py --mode run --output renders/`

### Layperson Communication Pattern

For physics concepts, use this structure:
1. **🏠 Think of it like...** - Everyday analogy
2. **🌍 Why it matters** - 3-bullet practical implications  
3. **👉 One thing to remember** - Memorable takeaway

### Visualization Guidelines

- **Spacious Layout**: Prefer 2x2 grids over 3x4 (less cramped).
- **Colors**: Use vibrant palette (#FF6B6B, #4ECDC4, #45B7D1).
- **HIHO Threshold**: Always add `fig.add_vline(x=0.5, line_dash="dash", line_color="gold")` for coherence plots.
- **Reactivity**: Ensure plots update immediately on slider/dropdown changes by including the UI element in the cell arguments.

## Key Project Locations

| Resource | Path |
|----------|------|
| Marimo Notebooks | `notebooks/marimo/` |
| WASM Renders | `renders/` |
| Retrospectives | `src/cohezion/knowledge_graph/retrospectives/` |
| Learnings | `src/cohezion/knowledge_graph/` |

## SurrealDB Schema

Tables used:
- `learnings` - Indexed discoveries with confidence scores
- `notebook_journeys` - FLUME trajectory records
- `overnight_mission` - Autonomous research runs
