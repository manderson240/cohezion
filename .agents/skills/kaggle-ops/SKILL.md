---
name: kaggle-ops
description: Comprehensive operational runbook for Kaggle competitions. Automates portfolio auditing, offline Rust wheel bundling, pre-submission IV&V gating, notebook push/submit dispatching, and high-water mark ratchet tracking across active competitions (ARC-2/3, RSNA Knee, CASMI26, Biohub, Kaggriculture).
---

# Kaggle Competition Operations (Kaggle-Ops)

## Overview
This skill provides a unified, end-to-end operational workflow for Kaggle competitions. It integrates our native Rust PyO3 accelerators, Two-Party IV&V cryptographic gatekeepers, automated notebook submission protocols, and 24/7 background ascent daemons.

---

## Core Operations

### 1. Active Portfolio Leaderboard Audit
Audit team rankings, scores, and prize gap distances across active monetary competitions (strictly excluding expired competitions and Pokémon TCG):
```bash
.venv/bin/python scripts/kaggle/leaderboard_inspector.py --sync-surreal
```

### 2. Offline Rust Wheel Packaging
Bundle `cohezion-physics-core` into an offline Linux x86_64 `.whl` and Kaggle dataset bundle for zero-latency execution inside Kaggle containers:
```bash
PYTHONPATH=src .venv/bin/python scripts/kaggle/package_rust_wheel_for_kaggle.py --verify
```
* Kaggle Dataset ID: `manderson240/cohezion-physics-core-wheel`
* Offline install inside notebook: `!pip install --no-index --find-links=/kaggle/input/cohezion-physics-core-wheel cohezion_physics_core`

### 3. IV&V Gatekept Notebook Submission
Code competitions (ARC-AGI-2, ARC-AGI-3, RSNA Knee, CASMI26) strictly reject local file uploads with HTTP 400 `FAILED_PRECONDITION`. All submissions must be dispatched via `kaggle_submit.py` in notebook mode:
```bash
PYTHONPATH=src .venv/bin/python scripts/kaggle/kaggle_submit.py notebook \
  -c <competition-slug> \
  -k manderson240/<kernel-slug> \
  -f submission.csv \
  -m "Cohezion SOTA vX: Description" \
  --code-path <local-notebook-path>
```
* **Two-Party IV&V Gate**: The gatekeeper verifies HMAC cryptographic attestation from `ivv-authority-daemon-v1` before contacting the Kaggle API.
* **Docker-Python Verifier**: Scans notebook AST and cross-references all imported modules against Kaggle's official `gcr.io/kaggle-images/python` container manifest.
* **Dynamic Version Resolution**: If `--version` is omitted, automatically queries the Kaggle SDK (`ApiGetKernelRequest`) to lock onto the latest completed execution version.

### 4. Background Ascent Daemon Monitoring
Monitor active 24/7 autonomous ascent swarms:
- **R-Zero Challenger vs Solver Swarm**: `tmux capture-pane -pt r-zero-swarm -S -50`
- **Kaggle Midnight Automated Submitter**: `tmux capture-pane -pt kaggle-midnight -S -50`
- **Kaggle Sentinel Submission Monitor**: `tmux capture-pane -pt kaggle-sentinel -S -50`

* **Dynamic High-Water Mark Ratchet**: Automatically advances $S_{\text{floor}}$ upon improvement ($\Delta > 0$).
* **Rollback & Invariant Extraction**: Automatically rolls back regressed candidates and logs findings to SurrealDB (`experiment_run`).
