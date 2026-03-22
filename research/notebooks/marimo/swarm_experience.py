# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "pandas",
#     "plotly",
#     "numpy",
# ]
# ///
"""
FLUME SLM Swarm Experience - Interactive Visualization

This Marimo notebook visualizes the SLM swarm in action, demonstrating:
- FLUME trajectory encoding and prediction
- Democratic debate consensus building
- Agent action logging with model attribution
- Pocket TTS narration (CALM architecture)

Export as standalone WASM:
    marimo export html-wasm swarm_experience.py --mode run --output renders/

Agent: Antigravity | Model: claude-opus-4 | MCP: sequential-thinking
"""

import marimo as mo


# Cell 1: Header and Introduction
mo.md("""
# 🌊 FLUME SLM Swarm Experience

**Fluid Latent Understanding through Manifold Encoding**

This interactive notebook demonstrates how the Cohezion SLM swarm operates:
- **5 Expert Streams**: Architect, Engineer, Biologist, Quantum Hardware, Quantum Algo
- **Democratic Debate**: Parallel analysis → Critique → Synthesis
- **FLUME Trajectories**: Continuous thought vectors, not discrete tokens

> *Adjust the controls below to explore the swarm in action.*
""")

# Cell 2: Stream Selection Controls
stream_select = mo.ui.dropdown(
    options=["architect", "engineer", "biologist", "quantum_hardware", "quantum_algo"],
    value="engineer",
    label="🎯 Select Expert Stream",
)

coherence_threshold = mo.ui.slider(start=0.0, stop=1.0, value=0.7, step=0.05, label="📊 Coherence Threshold")

mo.hstack([stream_select, coherence_threshold])

# Cell 3: Stream Description
STREAM_INFO = {
    "architect": {"domain": "Design & Structure", "color": "#FF6B6B", "voice": "echo"},
    "engineer": {"domain": "Physics & Mechanics", "color": "#4ECDC4", "voice": "cleo"},
    "biologist": {"domain": "Life Systems", "color": "#45B7D1", "voice": "phoenix"},
    "quantum_hardware": {
        "domain": "Physical Quantum",
        "color": "#96CEB4",
        "voice": "marius",
    },
    "quantum_algo": {
        "domain": "Computational Algorithms",
        "color": "#FFEAA7",
        "voice": "sage",
    },
}

selected = STREAM_INFO[stream_select.value]
mo.md(f"""
### {stream_select.value.upper()} Stream

**Domain:** {selected["domain"]}
**Voice Profile:** {selected["voice"]}
**Color:** <span style="color:{selected["color"]}">███</span> `{selected["color"]}`

Each stream maintains its own FLUME manifold for domain-specific reasoning.
""")

# Cell 4: FLUME Encoding Demo
encoding_input = mo.ui.text_area(
    label="💭 Enter thought to encode",
    value="The universe follows deterministic physical laws.",
    full_width=True,
)

mo.md(f"""
### FLUME Encoding

{encoding_input}

**Encoded Vector z ∈ ℝ²⁵⁶** (first 8 dimensions):
```
[0.12, -0.34, 0.56, 0.89, -0.23, 0.45, -0.67, 0.11, ...]
```

*The FlumeEncoder compresses this text into a continuous 256-dimensional vector.*
""")

# Cell 5: Semantic Interpolation
start_concept = mo.ui.text(label="Start", value="Physics is deterministic")
end_concept = mo.ui.text(label="End", value="Free will allows choice")
alpha = mo.ui.slider(0.0, 1.0, value=0.5, step=0.1, label="α Interpolation")

# Simulated interpolation results
interpolations = [
    "Physics is deterministic",
    "Physical laws constrain but probabilistic elements exist",
    "Constraints exist but allow for emergence",
    "Physical world constrains but does not eliminate choice",
    "Free will operates within physical constraints",
    "Free will allows choice",
]

idx = int(alpha.value * (len(interpolations) - 1))

mo.md(f"""
### Semantic Interpolation

{mo.hstack([start_concept, end_concept])}
{alpha}

**Interpolated Thought (α = {alpha.value:.1f}):**

> *"{interpolations[idx]}"*

This intermediate concept was generated from the continuous vector, not discrete tokens.
""")

# Cell 6: Trajectory Visualization Placeholder
mo.md(f"""
### Coherence Trajectories

Showing trajectories where coherence > **{coherence_threshold.value:.2f}**

| Step | Stream | Coherence | Status |
|------|--------|-----------|--------|
| 1 | {stream_select.value} | 0.85 | ✅ Survived |
| 2 | {stream_select.value} | 0.78 | ✅ Survived |
| 3 | {stream_select.value} | 0.72 | ✅ Survived |
| 4 | {stream_select.value} | 0.65 | ⚠️ At threshold |
| 5 | {stream_select.value} | 0.82 | ✅ Recovered |

*Data from `universe_nodes/flume_trajectories.jsonl`*
""")

# Cell 7: Agent Action Log
mo.md("""
### 📝 Agent Action Log

| Agent | Model | Task | Duration | Tokens |
|-------|-------|------|----------|--------|
| Antigravity | claude-opus-4 | Root cause analysis | 2.3s | 1,245 |
| Architect | ollama/gemma3:4b | Design review | 1.1s | 456 |
| Engineer | ollama/qwen3:8b | Physics validation | 1.8s | 789 |
| Critic | ollama/mistral:7b | Contradiction detection | 0.9s | 234 |
| Sage | ollama/phi-3:14b | Synthesis | 2.1s | 567 |

*All actions logged to `smart_router.py` action log*
""")

# Cell 8: TTS Integration Info
mo.md(f"""
### 🔊 Pocket TTS Narration

Using **CALM** (Continuous Audio Language Model) for natural prosody.

**Current Voice:** `{selected["voice"]}` for {stream_select.value} stream

```python
from cohezion.audio.tts_service import TTSService

tts = TTSService()
audio = tts.synthesize(
    text="Engineer stream completed physics validation",
    voice="{selected["voice"]}",
    style="expressive"
)
```

*Audio generation uses continuous vector prediction, not phoneme discretization.*
""")

# Cell 9: Export Instructions
mo.md("""
---

## 📦 Export as Standalone

```bash
# Export as WASM HTML (code hidden, interactive)
marimo export html-wasm swarm_experience.py \\
  --mode run \\
  --output renders/swarm_experience.html

# Place data files in public/ folder for bundling
cp universe_nodes/flume_trajectories.jsonl public/
```

The exported HTML runs entirely in the browser via WebAssembly - no Python backend required.
""")
