---
name: visualization-prime
description: "Expertise in high-dimensional (12D) data visualization and interactive explainability. Specializes in mapping abstract PhysicsState vectors (Mass, Complexity, Sentiment, etc.) to intuitive, multi-modal interfaces using Plotly, Radar charts, and PCA projections."
metadata:
  version: "v0.1"
  concepts: ["PCA (Principal Component Analysis)", "Radar (Spider) Charts", "Color Encoding", "Interactive Widgets"]
  source: "src/cohezion/skills/VISUALIZATION_PRIME.md"
---

# SKILL: VISUALIZATION_PRIME

## DOMAIN EXPERTISE
Expertise in high-dimensional (12D) data visualization and interactive explainability. Specializes in mapping abstract `PhysicsState` vectors (Mass, Complexity, Sentiment, etc.) to intuitive, multi-modal interfaces using Plotly, Radar charts, and PCA projections.

## KEY TEXTS & CONCEPTS
- **PCA (Principal Component Analysis)**: Reducing 12D vectors to 2D/3D for spatial storytelling.
- **Radar (Spider) Charts**: Visualizing dimension-by-dimension attributes of a single state/agent.
- **Color Encoding**: Mapping `Sentiment` to Blue/Red and `Coherence` to Alpha/Opacity.
- **Interactive Widgets**: Using Marimo Sliders/Dropdowns to traverse historical trajectories.

## INSTRUCTION
1.  **Select Perspective**:
    - Use Radar charts for "Deep Dives" into a single thought.
    - Use Scatter/Line plots for "Evolutionary Trajectories".
2.  **Apply HIHO Threshold**: Always annotate `0.5` on coherence/stability axes to show reality precipitation points.
3.  **Explain the Delta**: When visualizing state changes, highlight the dimensions with the largest variance (e.g., "Complexity spiked by 40% in this step").
4.  **Responsive Layouts**: Design for "Pulse Dashboards" that update automatically as SurrealDB nodes arrive.

### Example (Radar Chart Pattern)
```python
fig = px.line_polar(df, r='value', theta='dimension', line_close=True)
fig.update_traces(fill='toself')
```

## VERSION
v0.1

## SEE ALSO
PHYSICS_EXPLAINABILITY_PRIME, FLUME_INTEGRATION_PRIME
