---
type: antigravity-artifact
session_id: 48be5ea6-a6b4-42e1-adca-ac83660307e0
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.336
  stage: embryo
  cluster: Agents
---

# Fractal Universe Simulation Walkthrough

## Overview
I have implemented and launched a **Fractal Universe Simulator** to fill the gap in spatial and multi-agent simulation capabilities.

- **File**: `src/cohezion/simulation/fractal_universe.py`
- **Output**: `data/simulations/fractal_nexus/*.parquet`
- **Log**: `fractal_universe.log`
- **Duration**: 3 Hours

## What It Does
The simulation models a 64x64 toroidal grid of "Manifold Sectors" (Void, Resonant, Glitch, Nexus). 128 "Stabilizer Agents" navigate this grid.
- **Goal**: Maintain HIHO stability (0.5 coherence).
- **Physics**: 
    - **Entropy Diffusion**: Sectors exchange entropy with neighbors.
    - **Heat Transfer**: High energy sectors produce entropy.
    - **Global Field**: Universe pulls sectors toward global average stability.
- **Agents**: 
    - **Memory**: Agents remember past effectiveness.
    - **Vectors**: 12D state vectors warped by sector interactions (RealityStabilizer).
- **Logging**: Captures spatial trajectories and energy states for later analysis.

## Monitoring
The simulation is running in the background.

## Automated Analysis
When the simulation ends (or is interrupted), it will automatically:
1.  Run `src/cohezion/simulation/analysis_prime.py`
2.  Generate a report: `SIMULATION_REPORT.md`
3.  Generate a plot: `renders/stability_trend.png`

You can also trigger analysis manually at any time:
```bash
python3 src/cohezion/simulation/analysis_prime.py
```

### 1. Check Logs
To see the ASCII map updates and agent status:
```bash
tail -f fractal_universe.log
```

### 2. Check System Load
Ensure the simulation (python3 process) is not consuming excessive CPU:
```bash
htop
```
(Look for `fractal_universe.py`)

### 3. Fractal Dashboard (Visualizer)
To see the high-fidelity visualization (Streamlit + Plotly):
```bash
.venv/bin/streamlit run src/cohezion/ui/fractal_dashboard.py
```
This launches a web UI at `http://localhost:8501`.

### 4. Verify Data
Check that parquet shards are being generated:
```bash
ls -l data/simulations/fractal_nexus/
```

## Next Steps
After ~3 hours, the simulation will exit automatically. You can then analyze the `fractal_universe.log` or load the parquet files using `SimulationLogger`.

## Related Vault Notes

- [[cohezion]]
- [[fractal-universe]]
- [[universe-simulation]]
