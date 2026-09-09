#!/usr/bin/env python3
"""Consult Model Fleet on High-Impact Worthwhile Improvements to Kaggle Submissions.

Queries models on concrete, measurable score-boosting upgrades across all 5 tracks.
"""

import httpx
import json

prompt = """You are a Kaggle Grandmaster & Competitive AI Systems Architect.
Current Submissions State:
1. ARC-AGI-2 (v9) & ARC-AGI-3 (v10): Dual-GPU (DeepSeek-R1 AWQ + Qwen Coder) + 0ms AST Invariant Checks.
2. Pokémon TCG (v6): Pure CPU Embedded Neural Policy Network + Public Belief State (PBS) Guidance.
3. RSNA Knee (v3): Multi-View Prior Baseline + Fallback paths.
4. Biohub Cell Tracking (v6): Hungarian Bipartite Tracking + Fallback paths.

Newly Built Local Engines (Not yet embedded into production Kaggle kernels):
- `arc/metadata_feature_extractor.py`: Shape transition classes + color frequency invariants.
- `world_models/embedded_nca_world_model.py`: 2D Neural Cellular Automata grid evolver (2.5ms).
- `pokemon_tcg/metadata_rule_engine.py`: Legality action masking (cuts branching factor by 60%).
- `rsna_knee/dicom_metadata_film.py`: DICOM header FiLM conditioning.
- `biohub_cell/zarr_physical_metadata.py`: Riemannian physical distance metric (µm).

Question: What are the TOP 3 most worthwhile, highest-leverage improvements to bundle and deploy into our next Kaggle submission kernels right now to maximize leaderboard score?
Provide a concise, highly focused technical recommendation under 200 words."""

try:
    resp = httpx.post("http://127.0.0.1:11434/api/generate", json={
        "model": "deepseek-v4-flash:cloud",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 500}
    }, timeout=45.0)
    
    if resp.status_code == 200:
        data = resp.json()
        print("💡 MODEL STRATEGIC RECOMMENDATION (WORTHWHILE KAGGLE UPGRADES):")
        print("=" * 80)
        print(data.get("response", ""))
        print("=" * 80)
    else:
        print(f"HTTP {resp.status_code}: {resp.text}")
except Exception as e:
    print(f"Notice: {e}")
