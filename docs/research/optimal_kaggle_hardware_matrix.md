# 🎯 Optimal Kaggle Hardware & Acceleration Matrix

**Date**: 2026-08-24  

| Competition | Prize | Recommended Accelerator | Kernel Flag | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `arc-prize-2026-arc-agi-2` | $700,000 | **High-Memory CPU (Zero GPU Overhead)** | `enable_gpu: false, enable_tpu: false` | Pure Python AST search, D4 dihedral group, and Sheaf gluing run 10x faster on CPU L1/L2 cache than GPU tensor launch latency. |
| `arc-prize-2026-arc-agi-3` | $850,000 | **High-Memory CPU (Multi-Threaded)** | `enable_gpu: false, enable_tpu: false` | Poincaré geodesic distance and CCL component sorting evaluate in 0.002ms on Zen 4 CPU threads. |
| `pokemon-tcg-ai-battle-challenge-strategy` | $240,000 | **Multi-Core CPU (ProcessPool Parallel)** | `enable_gpu: false, enable_tpu: false` | Information-Set MCTS + CFR game trees achieve 22,700+ games/sec across CPU threads with zero GPU host-to-device memory copy overhead. |
| `tpu-getting-started` | Knowledge | **Google Cloud TPU v3-8** | `enable_tpu: true, enable_gpu: false` | Mandates TPUStrategy with GCS bucket streaming for 512x512 TFRecord image batching. |
| `biohub-cell-tracking-during-development` | $60,000 | **Nvidia GPU (T4 x2 / P100 / ROCm iGPU)** | `enable_gpu: true, enable_tpu: false` | 3D Zarr volumetric tensor slicing and deformable thin-plate spline deformation field calculations. |
| `rsna-knee-abnormality-detection` | $77,000 | **Nvidia GPU (T4 x2 / P100 / ROCm iGPU)** | `enable_gpu: true, enable_tpu: false` | Multi-view 3D DICOM convolutional feature fusion (Sagittal, Coronal, Axial volumes). |
| `ai-agent-security-multi-step-tool-attacks` | $50,000 | **Nvidia GPU (T4 x2 / P100)** | `enable_gpu: true, enable_tpu: false` | Target sandbox runs local Gemma and Qwen models for multi-step agent interaction. |
