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
.venv/bin/python scripts/kaggle/package_rust_wheel_for_kaggle.py --verify
```
* Kaggle Dataset ID: `manderson240/cohezion-physics-core-wheel`
* Offline install inside notebook: `!pip install --no-index --find-links=/kaggle/input/cohezion-physics-core-wheel cohezion_physics_core`

### 3. IV&V Gatekept Notebook Submission
Code competitions (ARC-AGI-2, ARC-AGI-3, RSNA Knee, CASMI26) strictly reject local file uploads. All submissions must be dispatched via `kaggle_submit.py` in notebook mode:
```bash
.venv/bin/python scripts/kaggle/kaggle_submit.py notebook \
  -c <competition-slug> \
  -k manderson240/<kernel-slug> \
  -f submission.csv \
  -m "Cohezion SOTA vX: Description" \
  -w
```
* The gatekeeper automatically enforces Two-Party IV&V verification and HMAC signing before dispatching to Kaggle.

### 4. Background Ascent Daemon Monitoring
Monitor the active 24/7 autonomous ascent loop:
```bash
tail -f /home/mike-anderson/.gemini/antigravity-cli/brain/80835800-7087-42b0-ae2a-5573c6be7538/.system_generated/tasks/task-30611.log
```
* **Dynamic High-Water Mark Ratchet**: Automatically advances $S_{\text{floor}}$ upon improvement ($\Delta > 0$).
* **Rollback & Invariant Extraction**: Automatically rolls back regressed candidates and runs Quad-Perspective Adversarial Review.
