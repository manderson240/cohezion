# NVIDIA Nemotron Model Reasoning Challenge

This directory contains our work on the [NVIDIA Nemotron Model Reasoning Challenge](https://www.kaggle.com/competitions/nvidia-nemotron-model-reasoning-challenge) from Kaggle.

## Overview

The challenge focuses on advancing reasoning techniques using NVIDIA's Nemotron open models on a novel benchmark. Our approach builds upon existing work done in a Gemini session that started a LoRA fine-tuning baseline for the Nemotron-3-Nano-30B model.

## Directory Structure

```
nvidia-nemotron-reasoning/
├── data/                 # Symlinked to competition data
│   ├── train.csv         # Training data (symlinked)
│   └── test.csv          # Test data (symlinked)
├── notebooks/            # Jupyter notebooks for exploration and experiments
│   ├── 00_gemini_baseline_lora.ipynb  # Existing work from Gemini session
│   ├── 01_environment_check.ipynb     # Environment validation
│   ├── 02_data_exploration.ipynb      # Data analysis and understanding
│   ├── 03_baseline_evaluation.ipynb   # Baseline model assessment
│   ├── 04_enhanced_lora.ipynb         # Enhanced LoRA experiments
│   ├── 05_prompt_engineering.ipynb    # Prompting techniques (CoT, ToT, etc.)
│   └── 06_final_solution.ipynb        # Final solution and submission prep
├── src/                  # Source code and utilities
│   ├── __init__.py
│   ├── competition_utils.py  # Challenge-specific utilities
│   ├── data_loader.py        # Data loading and preprocessing
│   ├── model_adapter.py      # Model loading and adaptation
│   ├── reasoning_techniques.py # Prompting and reasoning methods
│   └── trainer.py            # Training loops and evaluation
├── models/               # Model checkpoints and adapters
├── logs/                 # Training and experiment logs
├── submissions/          # Final submission files
├── README.md             # This file
├── PLAN.md               # Detailed project plan
└── requirements.txt      # Python dependencies
```

## Existing Foundation

This work builds upon a Gemini session that started:
- LoRA fine-tuning setup for `nvidia/Nemotron-3-Nano-30B-A3B`
- Installation of required dependencies: `mamba_ssm`, `causal-conv1d`, `peft`
- Basic model loading and adapter saving

See `notebooks/00_gemini_baseline_lora.ipynb` for the existing work.

## Getting Started

1. **Activate Environment**: `source ../../../../venv/bin/activate` (if using cohezion's venv)
2. **Check Environment**: Run `notebooks/01_environment_check.ipynb`
3. **Explore Data**: Run `notebooks/02_data_exploration.ipynb`
4. **Review Existing Work**: Examine `notebooks/00_gemini_baseline_lora.ipynb`
5. **Proceed with Enhancement**: Work through the numbered notebooks in order

## Credentials

Kaggle credentials are expected to be available in the cohezion root `.env` file or via standard Kaggle authentication methods.

## Competition Info

- **Host**: Kaggle
- **Challenge**: NVIDIA Nemotron Model Reasoning Challenge
- **URL**: https://www.kaggle.com/competitions/nvidia-nemotron-model-reasoning-challenge
- **Focus**: Reasoning enhancement using Nemotron models
- **Data**: Train.csv and Test.csv provided
