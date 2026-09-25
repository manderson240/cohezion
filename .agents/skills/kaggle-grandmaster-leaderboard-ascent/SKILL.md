---
name: kaggle-grandmaster-leaderboard-ascent
description: Use when auditing, analyzing, or climbing Kaggle competition leaderboards. Automates full leaderboard downloading, exact team ranking lookups, score gap calculations to Rank 1/3/10, V-Model verification gating (VG-1 to VG-4), and SurrealDB synchronization.
---

# Kaggle Grandmaster Leaderboard Ascent

## Overview
This skill provides an automated, mathematically grounded protocol for inspecting exact Kaggle competition positions, auditing gaps to podium prize tiers, enforcing V-Model verification gates, and orchestrating scientist digital twin agents to climb the leaderboards.

## Quick Start
To run a full audit across all active monetary competitions, calculate gaps to Rank 1, 3, and 10, and synchronize findings with SurrealDB:

```bash
uv run python scripts/kaggle/leaderboard_inspector.py --sync-surreal
```

## Core Protocol & Rules

### 1. Active Monetary Competitions Only
Strictly ignore expired competitions. Per explicit project mandate, strictly exclude Pokémon TCG.

### 2. Winnable Prize Valuation Policy
Always report **actually winnable payouts based on realistic target positions** (e.g. 1st–3rd place achievable cash), never gross collective prize money.

### 3. Verification Gates (VG-1 to VG-4)
Before submitting any kernel, bot, or agent archive:
1. **VG-1 (AST & Schema Gate)**:
   - Ensure zero syntax errors (`ast.parse()`).
   - Validate declarative schemas (e.g., ensure `thinking_config` is nested in `GenerateContentConfig` for Google ADK).
   - Ensure `def agent(obs, config=None)` is the trailing callable for simulation scripts.
2. **VG-2 (Local Emulation & Head-to-Head Gate)**:
   - Run deterministic local benchmarks (e.g., 100% win-rate vs SOTA baseline with positive coin delta).
3. **VG-3 (Resource & Hardware Bounds Gate)**:
   - Obey the Zero-Local-Weight Guardrail (0 MB host GPU VRAM).
   - Ensure runtime <9h and memory <10 GB on Kaggle cloud runners.
4. **VG-4 (Patch Non-Emptiness & Invariant Gate)**:
   - Ensure `git diff HEAD` is non-empty before calling `submit_patch()`.
   - Maintain forward-backward reciprocity in bipartite tracking.
   - Respect Kaggle daily submission allowances (e.g., 1/day SWE-bench reset at 00:00 UTC).

### 4. Scientist Digital Twin Allocation
- **Biohub 3D Cell Tracking**: Dr. Barbara McClintock & Dr. Ilya Prigogine
- **Kaggriculture Simulation**: Dr. John von Neumann & Dr. Claude Shannon
- **RSNA Knee Abnormality**: Dr. Richard Feynman & Dr. Barbara McClintock
- **ARC Prize 2026 (ARC-3/2)**: Dr. John von Neumann & Dr. Richard Feynman
- **Google Gemma 4 Dev Agent**: Dr. Leslie Lamport & Dr. John von Neumann
- **Enveda CASMI26 Molecule ID**: Dr. Ilya Prigogine & Dr. Claude Shannon
