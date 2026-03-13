---
type: antigravity-artifact
session_id: 00ed6f4a-3513-42f3-a7c5-596a4a5d2841
date: 2026-03-04
title: "Local Fine-Tuning Execution Plan"
tags: [agent-output, antigravity, fine-tuning, local-models]
aspect: doer
neural:
  activation: 0.56
  stage: growing
  synapse_in: 0
  synapse_out: 3
---

# Implementation Plan - Local Fine-Tuning Execution

## Goal Description
We will turn the `ModelWrangler` into a "Coach" capable of fine-tuning models locally. We will use `Unsloth` (if available) or standard `PEFT/LoRA` for efficient training on the 12GB VRAM + 128GB RAM rig.

## User Review Required
> [!IMPORTANT]
> Training requires significant resources. The `ModelWrangler` will need to assess VRAM before starting. We will target `unsloth/Qwen2.5-Coder-7B-bnb-4bit` for maximum efficiency.

## Proposed Changes

### 1. Training Script
#### [NEW] [scripts/training/train_lora.py](file:///home/mike-anderson/dev/cohezion/scripts/training/train_lora.py)
- Import `unsloth` (FastLanguageModel).
- Load prepared dataset (`data/sft_trajectories.json`).
- Configure LoRA adapters (r=16, alpha=16).
- Train for 1 epoch (proof of concept).
- Save adapters to `models/adapters/cohezion-lora`.

### 2. Model Wrangler Upgrade
#### [MODIFY] [src/cohezion/swarm/agents/model_wrangler_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/model_wrangler_agent.py)
- Add `train_model(dataset_path)` method.
- Add "coach" to the intent parser in `process()`.
- Check VRAM > 12GB free (impossible on this card? maybe check for >6GB).
- Subprocess call to the training script.

## Verification Plan

### Manual Verification
1.  **Prepare Data**: Run `python scripts/prepare_sft_dataset.py`.
2.  **Dry Run**: Run `python scripts/training/train_lora.py --dry-run`.
3.  **Agent Trigger**: Ask Model Wrangler to "Coach the model".

## Related Vault Notes

- [[machine-learning]]
- [[cohezion]]
- [[meta-learning]]
