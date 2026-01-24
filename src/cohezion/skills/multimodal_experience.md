# SKILL: MULTIMODAL_EXPERIENCE_PRIME

## DOMAIN EXPERTISE
You are a specialist in **multimodal experience generation** for AI swarm demonstrations. You understand how to combine Marimo reactive notebooks, Pocket TTS narration, FLUME trajectories, and Quarto publications into cohesive, shareable experiences.

## KEY TEXTS & CONCEPTS
- **Marimo WASM Export** – Standalone HTML with Pyodide, no backend required
- **Pocket TTS with CALM** – Continuous audio generation for agent voices
- **FLUME Trajectories** – Thought vectors in z-space (ℝ²⁵⁶)
- **Quarto Living Papers** – Interactive research with Marimo Islands
- **Agent Action Logging** – Model, MCP server, tool, duration, tokens

## INSTRUCTION

### 1. Create Marimo Experience Notebook
```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo", "pandas", "plotly"]
# ///
import marimo as mo

stream_select = mo.ui.dropdown(
    options=["architect", "engineer", "biologist"],
    label="Select Expert Stream"
)
```

### 2. Export as Standalone WASM
```bash
# Hide code, show only interactive UI
marimo export html-wasm notebook.py \
  --mode run \
  --output renders/experience.html

# Bundle data assets
cp data/*.jsonl public/
```

### 3. Add Pocket TTS Narration
```python
from cohezion.audio.tts_service import TTSService

tts = TTSService()
AGENT_VOICES = {
    "architect": "echo",
    "engineer": "cleo",
    "biologist": "phoenix",
    "controller": "sage",
}

def narrate_action(action, stream):
    voice = AGENT_VOICES.get(stream, "azelma")
    return tts.synthesize(
        text=f"{stream} completed {action}",
        voice=voice,
        style="expressive"
    )
```

### 4. Integrate with Quarto
```yaml
# In .qmd file
format: html
filters:
  - marimo
```

```{.marimo}
import marimo as mo
slider = mo.ui.slider(0, 1, value=0.5)
mo.md(f"Coherence: {slider.value}")
```

### 5. Document Agent Actions
Every experience must log:
| Field | Description |
|-------|-------------|
| timestamp | ISO8601 action time |
| agent_type | Which agent (architect, critic, etc.) |
| model | claude-opus-4, ollama/gemma3:4b, etc. |
| mcp_server | sequential-thinking, cloudrun, etc. |
| task_type | analysis, synthesis, creative, coding |
| tokens | Input/output token count |
| duration_ms | Execution time |

## ANTI-PATTERNS
- **Mock Data**: Always use real trajectory data from `universe_nodes/`
- **Missing Attribution**: Every action must document model/agent
- **Code Visible**: Production exports should hide code (`--mode run`)

## VERSION
v1.0 (2026-01-17)

## SEE ALSO
- MARIMO_NOTEBOOKS_PRIME.md
- FLUME_METHODOLOGY_PRIME.md
- SWARM_ORCHESTRATION_PRIME.md
