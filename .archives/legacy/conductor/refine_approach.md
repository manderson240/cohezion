# Plan: Refine Approach for Kaggle Sprint

## Objective
Refine the approach for the NVIDIA Nemotron Challenge based on logs from v28 and v29.

## Analysis
- v28 failed due to wheel path and DNS resolution issues.
- v29 failed because `pip install` tried to modify Kaggle's `/kaggle/usr/lib/notebooks` read-only environment when installing local wheels.
- We also lack the `cutlass` dependency, which is required by `mamba3_step_fn.py`.

## Action Plan
1. Fix wheel installation logic in `kaggle_training_improved.py`:
   - Exclude core system packages like `setuptools` and `urllib3` from local offline installation.
   - Use `--target /tmp/pip_packages` to bypass the read-only file system errors.
   - Add `nvidia-cutlass` to the `MANDATORY_PACKAGES` list.
2. Trigger the `v30` sprint on Kaggle.
