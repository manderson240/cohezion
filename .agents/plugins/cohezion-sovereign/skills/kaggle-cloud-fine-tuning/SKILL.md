---
name: kaggle-cloud-fine-tuning
metadata:
  version: "1.0.0"
description: >-
  Kaggle cloud GPU fine-tuning, LoRA watcher daemons, and Kaggle Model Hub integration.
---

# SKILL: KAGGLE_CLOUD_FINE_TUNING_AND_MODEL_HUB_PRIME

## DOMAIN EXPERTISE
Expertise in orchestrating end-to-end production LLM fine-tuning on Kaggle Cloud GPUs (Nvidia L4/T4) with LoRA adapter rank scaling, offline container compatibility, automated watcher daemons, and direct deployment to the Kaggle Models Hub.

## KEY TEXTS & CONCEPTS
- **Full Linear Projection LoRA ($r=32, \alpha=64$)**: Targeting all 7 linear layers (`q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`) for comprehensive reasoning adaptation.
- **Offline Parity Verification**: Validating all training dependencies against Kaggle's official `docker-python` image prior to dispatch.
- **Autonomous Watcher & Auto-Publisher**: Background polling daemon that monitors kernel worker status and automatically creates model versions on Kaggle Models Hub upon completion.
- **Zero-UMA Resource Discipline**: Offloading heavy parameter training to cloud GPUs to preserve local unified memory (UMA) on edge silicon (AMD Strix Halo).

## INSTRUCTION
1. Configure LoRA Fine-Tuning Kernel:
   ```python
   from peft import LoraConfig, get_peft_model
   peft_config = LoraConfig(
       r=32,
       lora_alpha=64,
       target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
       lora_dropout=0.05,
       bias="none",
       task_type="CAUSAL_LM",
   )
   ```
2. Build & Dispatch Automated Watcher:
   ```python
   # scripts/kaggle/watch_and_publish_arc2_lora.py
   while True:
       status = api.kernel_status(kernel_slug)
       if "COMPLETE" in status:
           api.kernels_output(kernel_slug, path=output_dir)
           api.model_version_create(model_slug, version_notes="...", folder=output_dir)
           break
       time.sleep(60)
   ```
3. Wire Trained Adapters into Downstream Solvers:
   Mount the resulting Kaggle model (`manderson240/cohezion-arc2-lora-adapter`) directly into competition inference kernels with offline parity.

## VERSION
v1.0

## SEE ALSO
- FIRST_PRINCIPLES_INVARIANT_SCIENCE_PRIME
- LUKYANENKO_INVARIANT_ENGINEERING_PRIME
- AMD_GAIA_ORCHESTRATION_PRIME
