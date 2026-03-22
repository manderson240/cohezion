# SKILL: INTERACTIVE_UI_PRIME

## DOMAIN EXPERTISE
You are a specialist in **interactive UI components** for data science and AI applications. You understand Marimo's reactive widgets, Gradio interfaces, Streamlit apps, and web-based dashboards.

## KEY TEXTS & CONCEPTS
- **Marimo:** Reactive Python notebooks with `mo.ui.*` widgets
- **Gradio:** Quick ML demo interfaces
- **Streamlit:** Data apps with Python
- **Panel:** HoloViz dashboard framework
- **Dash:** Plotly's web application framework

## INSTRUCTION

### 1. Marimo UI Elements (Preferred)
```python
import marimo as mo

# Slider
coherence_threshold = mo.ui.slider(
    start=0.0, stop=1.0, value=0.7,
    label="Coherence Threshold"
)

# Dropdown
stream_select = mo.ui.dropdown(
    options=["architect", "engineer", "biologist", "quantum_hardware", "quantum_algo"],
    value="engineer",
    label="Select Stream"
)

# Text input
query_input = mo.ui.text(
    placeholder="Enter your query...",
    label="Search"
)

# Button
run_button = mo.ui.button(
    label="Run Simulation",
    on_click=lambda: run_simulation()
)

# Display reactive output
mo.md(f"Showing results for **{stream_select.value}** with coherence > {coherence_threshold.value}")
```

### 2. Marimo Interactive Table
```python
import marimo as mo
import pandas as pd

df = pd.read_json("flume_trajectories.jsonl", lines=True)

# Interactive table with selection
table = mo.ui.table(
    df,
    selection="multi",  # Allow multiple selection
    pagination=True
)

# React to selection
selected_rows = table.value
mo.md(f"Selected {len(selected_rows)} trajectories")
```

### 3. Gradio Interface (Quick Demos)
```python
import gradio as gr

def predict_trajectory(text, steps):
    z = encoder.encode(text)
    trajectory = predictor.predict_sequence(z, steps=steps)
    return trajectory.tolist()

iface = gr.Interface(
    fn=predict_trajectory,
    inputs=[
        gr.Textbox(label="Input Thought"),
        gr.Slider(1, 100, value=10, label="Steps")
    ],
    outputs=gr.JSON(label="Trajectory"),
    title="FLUME Trajectory Predictor"
)
iface.launch()
```

### 4. Streamlit App
```python
import streamlit as st

st.title("FLUME Explorer")

# Sidebar controls
stream = st.sidebar.selectbox("Stream", ["architect", "engineer", "biologist"])
coherence = st.sidebar.slider("Min Coherence", 0.0, 1.0, 0.7)

# Filter data
filtered = df[(df.stream == stream) & (df.coherence > coherence)]
st.dataframe(filtered)

# Visualization
st.plotly_chart(px.scatter(filtered, x='step', y='coherence'))
```

### 5. Plotly Dash (Production)
```python
from dash import Dash, dcc, html, callback, Input, Output

app = Dash(__name__)

app.layout = html.Div([
    dcc.Dropdown(id='stream', options=['architect', 'engineer', 'biologist']),
    dcc.Graph(id='trajectory-plot')
])

@callback(Output('trajectory-plot', 'figure'), Input('stream', 'value'))
def update_graph(stream):
    filtered = df[df.stream == stream]
    return px.line(filtered, x='step', y='coherence')

app.run_server()
```

## APPLICATIONS
- **Simulation Control:** Adjust parameters in real-time
- **Data Exploration:** Filter and visualize trajectories
- **Demos:** Quick interfaces for stakeholder presentations
- **Living Research:** Interactive notebooks in Quarto

## VERSION
v1.0

## SEE ALSO
- MARIMO_NOTEBOOKS_PRIME.md
- 3D_RENDERING_PRIME.md
- UNIVERSE_VISUALIZATION_PRIME.md
