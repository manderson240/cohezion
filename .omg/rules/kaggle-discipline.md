---
description: "Strict Kaggle competition rules, active track focus, and submission governance"
globs: ["scripts/kaggle/**", "src/cohezion/agi/kaggle*"]
alwaysApply: true
---

# Rule: Kaggle Discipline & Active Tracks Only

## Triggers
- Any task interacting with Kaggle CLI, kernels, datasets, or submissions.

## Enforced Behavior
1. **Active Tracks Only**: Strictly limit auditing and submissions to currently ACTIVE competitions:
   - ARC Prize 2026 (ARC-AGI-2, ARC-AGI-3, Paper Track)
   - Biohub Cell Tracking
   - RSNA Knee Abnormality Detection
   - Enveda CASMI26
   - Kaggriculture
2. **Strict Exclusions**: Never report on expired competitions. Explicitly exclude Pokémon TCG per user mandate.
3. **Code Competition Submission Protocol**:
   - For notebook competitions (RSNA, ARC-AGI-2, ARC-AGI-3, CASMI26), always use `api.competition_submit_code()` via `scripts/kaggle/kaggle_submit.py` with dynamic `kernel_version` resolution to avoid 400/403 Forbidden errors.
4. **Quota Stewardship**: Maximize daily submission quotas (resetting at 00:00:05 UTC) and weekly GPU/TPU hours without hitting throttling limits.
5. **Kaggle Docker-Python Pre-Submission Verification**: Every notebook or code artifact MUST pass AST static import verification against `Kaggle/docker-python/main/kaggle_requirements.txt` via `scripts/kaggle/docker_python_verifier.py` before dispatch to eliminate offline container failure risks.
6. **Concurrency Invariant Guard (`max_pending=1`)**: For single-worker / strict-concurrency competitions (e.g. Google Gemma 4 Developer Agent, RSNA Knee), NEVER dispatch when an earlier submission is `PENDING`. Polling daemons must check `check_is_pending()` to prevent `HTTP 400 FAILED_PRECONDITION`.
7. **Two-Party Cryptographic IV&V Separation**: Code creation and code verification must be architecturally separated. Every Kaggle submission must be backed by a cryptographic IV&V assertion signed by an independent verifier authority (`ivv-authority-daemon-v1` or `independent-*-auditor`).
8. **Hardware Aperture Protection**: All local narrative and verification calls must route through port 13305 (NPU `qwen3.5-4b-FLM` or CPU), preserving the 120GB GTT UMA aperture with zero host OOM pressure.
