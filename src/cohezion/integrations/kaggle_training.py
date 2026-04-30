import json
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class KaggleTrainingManager:
    """
    Manages the generation of LoRA training scripts and Kaggle notebooks
    for the Nemotron reasoning challenge.
    """

    def __init__(self):
        pass

    def generate_lora_config(
        self, r: int = 8, alpha: int = 16, dropout: float = 0.05, target_modules: list[str] = None
    ) -> dict[str, Any]:
        """
        Generate LoRA configuration for PEFT.
        """
        if target_modules is None:
            # Default target modules for Nemotron architecture
            target_modules = ["x_proj", "embeddings", "in_proj", "out_proj"]

        return {
            "r": r,
            "lora_alpha": alpha,
            "target_modules": target_modules,
            "lora_dropout": dropout,
            "bias": "none",
            "task_type": "CAUSAL_LM",
            "peft_type": "LORA",
        }

    def generate_adapter_config(self, base_model_name: str) -> dict[str, Any]:
        """
        Generate the adapter_config.json required for submission.
        """
        return {
            "base_model_name_or_path": base_model_name,
            "peft_type": "LORA",
            "task_type": "CAUSAL_LM",
        }

    async def prepare_notebook(self, code: str, output_path: Path) -> None:
        """
        Wrap Python code into a Jupyter Notebook format for Kaggle.
        """
        notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [code],
                }
            ],
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {
                    "codemirror_mode": {"name": "ipython", "version": 3},
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.10.12",
                },
            },
            "nbformat": 4,
            "nbformat_minor": 4,
        }

        with open(output_path, "w") as f:
            json.dump(notebook, f, indent=2)

        logger.info(f"Prepared Kaggle notebook at {output_path}")

    def get_training_script_template(self) -> str:
        """
        Returns the core training script template to be run on Kaggle.
        """
        return """
import os
import subprocess
import sys

# 1. Install mandatory dependencies
print("Installing mandatory dependencies...")
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q",
    "mamba_ssm", "causal-conv1d", "peft",
])

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
from datasets import load_dataset

# 2. Configuration
model_id = "nvidia/Nemotron-3-Nano-30B-A3B"
# The competition data is attached via the competitionId in metadata
# and mounted at /kaggle/input/[competition-id]
competition_id = "nvidia-nemotron-model-reasoning-challenge"
dataset_path = f"/kaggle/input/{competition_id}/train.csv"

print(f"Checking for dataset at {dataset_path}...")
if not os.path.exists(dataset_path):
    print(f"ERROR: Dataset not found at {dataset_path}")
    print("Files in /kaggle/input:")
    print(os.listdir("/kaggle/input"))
    sys.exit(1)

# 3. Load model in BF16
print(f"Loading model {model_id} in BF16...")
try:
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        device_map="auto"
    )
except Exception as e:
    print(f"ERROR loading model: {e}")
    sys.exit(1)

# 4. Configure LoRA
print("Configuring LoRA...")
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["x_proj", "embeddings"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# 5. Save baseline adapter
print("Saving baseline LoRA adapter...")
model.save_pretrained("nemotron_lora_adapter")
print("Baseline adapter saved successfully!")
"""
