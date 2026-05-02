# Nemotron v35 Auto-Submission Monitor

**Created**: 2026-04-28  
**Cron Job**: `nemotron-v35-submission-monitor` (id: c98ba598dfd5)  
**Schedule**: Every 5 minutes  
**Status**: ACTIVE

## What It Does
1. Polls Kaggle kernel `manderson240/nemotron-lora-sft-v35` status every 5 minutes
2. When status is COMPLETE:
   - Auto-submits to `nvidia-nemotron-model-reasoning-challenge`
   - Reports back submission status (PENDING → public score)
   - Stops monitoring
3. When status is ERROR:
   - Downloads log, reports error cause
   - Stops monitoring
4. When RUNNING/PENDING: continues polling

## Kernel Details
- **v34**: First attempt, ERROR (FileNotFoundError: train.csv path issue)
- **v35**: Fixed train.csv resolution using `os.walk` across all input dirs
- **Training**: 3 epochs, LoRA rank-32, bf16, gradient checkpointing, ~9,500 examples
- **Expected time**: 20-40 minutes on Kaggle GPU

## Last Known Score
- v20: 0.49 (baseline Blackwell G4 LoRA)
- v22-v33: Various errors
- v35: Currently RUNNING

## To Stop Monitoring
```bash
hermes cronjob pause nemotron-v35-submission-monitor
# or
hermes cronjob remove nemotron-v35-submission-monitor
```

## To Check Manually
```bash
kaggle kernels status manderson240/nemotron-lora-sft-v35
kaggle competitions submissions -c nvidia-nemotron-model-reasoning-challenge
```
