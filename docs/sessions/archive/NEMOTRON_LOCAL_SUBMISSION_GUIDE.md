# Nemotron LoRA — Local Training + Kaggle Submission Guide

## Background
- Kaggle GPU kernels can no longer pip-install packages in non-interactive sessions
- v20 scored 0.49 interactively (via browser) but all pushed kernels fail
- Solution: Train locally on your AMD Strix Halo, submit zip to Kaggle

## Prerequisites
```bash
# 1. Install dependencies (already on your system)
pip install torch transformers peft datasets accelerate

# 2. Download competition data
kaggle competitions download -c nvidia-nemotron-model-reasoning-challenge
unzip nvidia-nemotron-model-reasoning-challenge.zip

# 3. Download base model (or use Lemonade server)
# Option A: Via HuggingFace
huggingface-cli download nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16

# Option B: Via Lemonade (already running on localhost:13307)
# The model is already served there
```

## Run Training
```bash
cd /tmp
python /home/mike-anderson/dev/cohezion/src/cohezion/competition/nemotron_solver/train_local_submit.py
```

This will:
- Load train.csv
- Load Nemotron-3-Nano-30B (or fail gracefully with instructions)
- Train LoRA rank-32 for 1 epoch
- Save to /tmp/nemotron_lora_local/
- Create /tmp/submission.zip

## Submit to Kaggle
```bash
kaggle competitions submit -c nvidia-nemotron-model-reasoning-challenge \
    -f /tmp/submission.zip \
    -m "Local LoRA training v1"
```

## Expected Result
- Public score from leaderboard (should improve on 0.49)
- adapter_config.json + adapter_model.safetensors inside zip

## Next Steps to Improve Score
1. Use symbolic solver traces for training (verified ~54.6% correct)
2. Filter to only verified examples
3. More epochs (2-3)
4. Tune lr and grad_accum
5. Chat template with \boxed{} formatting

## Files Created
- /home/mike-anderson/dev/cohezion/src/cohezion/competition/nemotron_solver/train_local_submit.py
- /tmp/submission.zip (after running)
