---
name: kaggle-grandmaster-leaderboard-ascent
description: Use when auditing, analyzing, or climbing Kaggle competition leaderboards. Automates full leaderboard downloading, exact team ranking lookups, score gap calculations to Rank 1/3/10, V-Model verification gating (VG-1 to VG-4), and SurrealDB synchronization.
---

# Kaggle Grandmaster Leaderboard Ascent

## Overview
This skill provides an automated, mathematically grounded protocol for inspecting exact Kaggle competition positions, auditing gaps to podium prize tiers, enforcing V-Model verification gates, validating Two-Party Cryptographic IV&V assertions, and orchestrating scientist digital twin agents to climb the leaderboards.

## Quick Start
To run a full audit across all active monetary competitions, calculate gaps to Rank 1, 3, and 10, and synchronize findings with SurrealDB:

```bash
PYTHONPATH=src .venv/bin/python scripts/kaggle/leaderboard_inspector.py --sync-surreal
```

## Daily Quota & Cadence Strategy
Kaggle competitions have strict, non-negotiable daily submission limits that reset at 00:00:00 UTC:

| Competition | Prize Pool | Daily Limit | Quota Strategy | Dispatch Engine |
| :--- | :---: | :---: | :--- | :--- |
| **ARC-AGI-3** | $850,000 | **1 / day** | Pre-execute kernel during day; auto-dispatch at `00:00:05 UTC` via `queue_midnight_all_competitions.py` | `kaggle_submit.py notebook` |
| **ARC-AGI-2** | $700,000 | **1 / day** | Pre-execute Quad-L4 LoRA kernel; auto-dispatch at `00:00:05 UTC` | `kaggle_submit.py notebook` |
| **RSNA Knee** | $77,000 | **5 / day** | Staged daytime calibration (Slot 1: 00:00 UTC, Slot 2: 03:00 UTC, Slot 3: 11:00 UTC, Slot 4: 17:00 UTC, Slot 5: 22:00 UTC) | `kaggle_submit.py notebook` |
| **Enveda CASMI26**| $50,000 | **5 / day** | Iterative ablation ladder (dual FPNet neural ensemble + full parsimony + ranker blending) | `kaggle_submit.py notebook` |
| **Gemma 4 Dev** | $65,000 | **1 / day** | Evaluated via fast-inference container; dispatched via notebook submission | `kaggle_submit.py notebook` |
| **NFL BDB 2027** | $100,000 | **5 / day** | Kinematic Voronoi space-control and D4 equivariant player tracking | `kaggle_submit.py notebook` |

## Core Protocol & Rules

### 1. Active Monetary Competitions Only
Strictly filter all audits and submissions to active, unexpired competitions (Rule 8). Per explicit project mandate, strictly ignore and exclude Pokémon TCG.

### 2. Winnable Prize Valuation Policy
Always report **actually winnable payouts based on realistic target positions** (e.g. 1st–3rd place achievable cash), never gross collective prize money.

### 3. Verification Gates (VG-1 to VG-5)
Before submitting any kernel, bot, or agent archive:
1. **VG-1 (AST & Schema Gate)**:
   - Ensure zero syntax errors (`ast.parse()`).
   - Validate declarative schemas.
2. **VG-2 (Local Emulation & AutoHarness Gate)**:
   - Run deterministic local benchmarks (AutoHarness AST bytecode verifiers).
3. **VG-3 (Resource & Hardware Bounds Gate)**:
   - Obey the Zero-Local-Weight Guardrail (0 MB host GPU VRAM).
   - Ensure runtime <9h and memory <10 GB on Kaggle cloud runners.
4. **VG-4 (Patch Non-Emptiness & Invariant Gate)**:
   - Ensure code changes are verified against baseline regression.
   - Maintain strict monotonic improvement ($S_{\text{candidate}} \ge S_{\text{floor}}$).
5. **VG-5 (Two-Party Cryptographic IV&V Authority Gate)**:
   - All submissions MUST hold a valid, HMAC-signed assertion from `ivv-authority-daemon-v1`.
   - Independent verification is required: creator agent cannot self-sign.

### 4. Scientist Digital Twin Allocation
- **RSNA Knee Abnormality**: Dr. Richard Feynman & Dr. Barbara McClintock (Copula rank alignment & finding-specific temperature scaling)
- **Enveda CASMI26 Molecule ID**: Dr. Ilya Prigogine & Dr. Claude Shannon (Non-equilibrium thermodynamics & mass-spec entropy matching)
- **ARC Prize 2026 (ARC-3/2)**: Dr. John von Neumann & Dr. Richard Feynman (Monadic Markov cellular automata & cellular game theory)
- **Google Gemma 4 Dev Agent**: Dr. Leslie Lamport & Dr. John von Neumann (Formal verification & distributed invariant consensus)
