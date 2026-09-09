#!/usr/bin/env python3
import httpx
import json

prompt = """Compare Cohezion to the current industry state-of-the-art in 3 areas:
1. ARC Prize (Brute force LLM sampling like Ryan Greenblatt vs Cohezion AutoHarness + JEPA + Bioelectric NCA).
2. Agent Swarms (Cloud API wrappers like CrewAI/AutoGen vs Cohezion Sovereign Strix Halo + SystemWideFleetLock + SurrealDB/EventBus).
3. Cognitive Physics (Next-token prediction vs Cohezion 2048D Poincare + Symmetry Breaking).

Give a concise markdown table with: Dimension, Industry Standard, Cohezion Advantage, and Cohezion Risk/Vulnerability."""

try:
    resp = httpx.post("http://localhost:11434/api/generate", json={
        "model": "deepseek-v4-pro:cloud",
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 450}
    }, timeout=30.0)
    print(resp.json().get("response", ""))
except Exception as e:
    print(f"Error: {e}")
