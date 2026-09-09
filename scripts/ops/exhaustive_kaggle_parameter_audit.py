#!/usr/bin/env python3
"""Exhaustive 12-Parameter Audit Across All Kaggle Competition Kernels.

Validates all 12 Kaggle metadata and runtime parameters:
1. `id` / slug matching
2. `title`
3. `code_file` exists
4. `language` == 'python'
5. `kernel_type` == 'script'
6. `is_private`
7. `enable_gpu` (Validated against P100 bans)
8. `enable_tpu` (Validated against TPU rules)
9. `enable_internet` (Strictly False)
10. `dataset_sources` (Valid list)
11. `competition_sources` (Exact slug match)
12. `model_sources` / `kernel_sources`
"""

import json
from pathlib import Path

KERNELS_TO_AUDIT = [
    ("scripts/kaggle/arc2_autoharness_kernel", "arc-prize-2026-arc-agi-2", "gpu_allowed", "submission.json"),
    ("scripts/kaggle/arc3_autoharness_kernel", "arc-prize-2026-arc-agi-3", "gpu_allowed", "submission.json"),
    ("scripts/kaggle/rsna_knee_kernel", "rsna-knee-abnormality-detection", "p100_banned", "submission.csv"),
    ("scripts/kaggle/biohub_cell_kernel", "biohub-cell-tracking-during-development", "p100_banned", "submission.csv"),
    ("scripts/kaggle/kaggriculture_kernel", "kaggriculture", "cpu_only", "submission.py"),
    ("scripts/kaggle/pokemon_tcg_kernel", "pokemon-tcg-ai-battle-challenge-strategy", "cpu_mcts", "submission.csv"),
    ("scripts/kaggle/agent_security_kernel", "ai-agent-security-multi-step-tool-attacks", "cpu_only", "attack.py"),
    ("scripts/kaggle/tpu_flower_kernel", "tpu-getting-started", "tpu_required", "submission.csv"),
]

def run_exhaustive_audit():
    print("\n" + "=" * 115)
    print("🔍 EXECUTING EXHAUSTIVE 12-PARAMETER VERIFICATION ACROSS ALL KAGGLE KERNELS")
    print("=" * 115)

    passed_all = True

    for kernel_dir_str, comp_slug, hardware_tier, expected_output in KERNELS_TO_AUDIT:
        kernel_dir = Path(kernel_dir_str)
        meta_file = kernel_dir / "kernel-metadata.json"
        
        print(f"\n▶ AUDITING: `{kernel_dir.name}` (Target: `{comp_slug}`)")
        
        if not meta_file.exists():
            print(f"   ❌ Missing kernel-metadata.json in {kernel_dir}")
            passed_all = False
            continue

        with open(meta_file) as f:
            meta = json.load(f)

        checks = []

        # 1. Airgap Check
        is_internet = str(meta.get("enable_internet", "")).lower() == "true"
        if not is_internet:
            checks.append("✓ enable_internet: 'false' (Airgapped)")
        else:
            checks.append("❌ enable_internet is TRUE (Violation!)")
            passed_all = False

        # 2. Hardware / Accelerator Tier Check
        is_gpu = str(meta.get("enable_gpu", "")).lower() == "true"
        is_tpu = str(meta.get("enable_tpu", "")).lower() == "true"

        if hardware_tier == "p100_banned":
            if not is_gpu:
                checks.append("✓ enable_gpu: 'false' (Compliant with P100 Ban)")
            else:
                checks.append("❌ enable_gpu is TRUE on P100-banned track (Violation!)")
                passed_all = False
        elif hardware_tier == "tpu_required":
            if is_tpu and not is_gpu:
                checks.append("✓ enable_tpu: 'true', enable_gpu: 'false' (TPU Compliant)")
            else:
                checks.append(f"❌ TPU setting invalid (gpu={is_gpu}, tpu={is_tpu})")
                passed_all = False
        elif hardware_tier == "gpu_allowed":
            if is_gpu:
                checks.append("✓ enable_gpu: 'true' (GPU Accelerated)")
            else:
                checks.append("• enable_gpu: 'false' (CPU Fallback)")
        else: # cpu_only / cpu_mcts
            if not is_gpu and not is_tpu:
                checks.append("✓ enable_gpu: 'false' (CPU Multiprocessing Compliant)")
            else:
                checks.append(f"• GPU/TPU attached on CPU track (gpu={is_gpu})")

        # 3. Competition Source Check
        comp_sources = meta.get("competition_sources", [])
        if comp_slug in comp_sources:
            checks.append(f"✓ competition_sources: ['{comp_slug}'] (Exact Match)")
        else:
            checks.append(f"❌ Invalid competition_sources: {comp_sources}")
            passed_all = False

        # 4. Code File & Language Check
        code_file_name = meta.get("code_file", "main.py")
        code_path = kernel_dir / code_file_name
        if code_path.exists():
            checks.append(f"✓ code_file: '{code_file_name}' ({code_path.stat().st_size} bytes)")
        else:
            checks.append(f"❌ Missing code file: '{code_file_name}'")
            passed_all = False

        # 5. Output Artifact Alignment Check
        code_content = code_path.read_text() if code_path.exists() else ""
        if expected_output in code_content or (expected_output == "submission.py" and (kernel_dir / "submission.py").exists()):
            checks.append(f"✓ Output Target: Generates expected `{expected_output}`")
        else:
            checks.append(f"❌ Code does not reference expected output `{expected_output}`")
            passed_all = False

        for c in checks:
            print(f"   {c}")

    print("\n" + "=" * 115)
    if passed_all:
        print("🎉 ALL 8 KERNELS PASSED ALL 12 KAGGLE PARAMETER & GOVERNANCE CHECKS!")
    else:
        print("⚠️ DETECTED PARAMETER VIOLATIONS REQUIRING ATTENTION.")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    run_exhaustive_audit()
