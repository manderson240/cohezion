#!/usr/bin/env python3
"""
Narration MCP Server 🎤

Exposes pocket-tts voice synthesis to the cortex.
"""

import sys
from pathlib import Path
from fastmcp import FastMCP
from pocket_tts import TTSModel
import scipy.io.wavfile

mcp = FastMCP("cohezion-narration")

@mcp.tool()
def list_voices():
    """List available pocket-tts narrator personalities."""
    return ["Alba", "Marius", "Javert", "Jean", "Fantine", "Cosette", "Eponine", "Azelma"]

@mcp.tool()
def generate_voiceover(text: str, voice: str = "Alba", filename: str = "narration.wav"):
    """Synthesize voiceover for simulation milestones."""
    output_path = Path("data/audio") / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        model = TTSModel.load_model()
        state = model.get_state_for_audio_prompt(voice)
        audio = model.generate_audio(state, text)
        scipy.io.wavfile.write(output_path, model.sample_rate, audio.numpy())
        return f"Success: {output_path}"
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    mcp.run()
