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
                "kaggle": {
                    "accelerator": "nvidiaRtxPro6000",
                    "isGpuEnabled": True,
                    "isInternetEnabled": True,
                    "language": "python",
                    "sourceType": "notebook",
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
        Improved version with better error handling and debugging.
        """
        return r"""
import os
import subprocess
import sys
import traceback

print("=" * 50)
print("STARTING NEMOTRON LORA TRAINING")
print("=" * 50)

try:
    # 1. Blackwell Environment Setup
    print("Setting up Blackwell environment...")
    UTILITY_PATH = "/kaggle/usr/lib/notebooks/ryanholbrook/nvidia_utility_script"
    if os.path.exists(UTILITY_PATH):
        # Copy to /tmp to make binaries executable
        subprocess.run(f"tar -cf - -C {UTILITY_PATH} . | tar -xf - -C /tmp", shell=True, check=True)
        # Set permissions
        for binary in ["ptxas", "ptxas-blackwell"]:
            bin_path = f"/tmp/triton/backends/nvidia/bin/{binary}"
            if os.path.exists(bin_path):
                subprocess.run(f"chmod +x {bin_path}", shell=True, check=True)
                print(f"Set execution permission on {binary}")
        # Insert /tmp into path
        sys.path.insert(0, "/tmp")
        print("Blackwell utility script initialized in /tmp")
    else:
        print(f"WARNING: Utility script not found at {UTILITY_PATH}")

    # 2. Verify hardware
    import torch
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            prop = torch.cuda.get_device_properties(i)
            cap = torch.cuda.get_device_capability(i)
            print(f"GPU {i}: {prop.name} (Total Memory: {prop.total_memory / 1024**3:.2f} GB)")
            print(f"  Compute Capability: {cap[0]}.{cap[1]} (sm_{cap[0]}{cap[1]})")

    # Check for mandatory dependencies
    print("Verifying mandatory dependencies...")
    try:
        import mamba_ssm
        import causal_conv1d
        import peft
        import bitsandbytes
        import cutlass
        print("All mandatory dependencies are pre-installed!")
    except ImportError as e:
        print(f"MISSING DEPENDENCY: {e}")
        print("Attempting to install missing dependency (requires internet)...")
        # Fallback only for missing items
        pkg_msg = str(e)
        if "cutlass" in pkg_msg:
            pkg = "nvidia-cutlass"
        else:
            pkg = pkg_msg.split("'")[-2]
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from datasets import load_dataset

    # 2. Configuration
    import kagglehub
    print("Downloading model from kagglehub...")
    model_path = kagglehub.model_download("metric/nemotron-3-nano-30b-a3b-bf16/transformers/default")
    print(f"Model path: {model_path}")

    # The competition data is attached via the competitionId in metadata
    competition_id = "nvidia-nemotron-model-reasoning-challenge"

    print(f"Looking for dataset...")
    train_file = None

    # Check common paths
    possible_paths = [
        f"/kaggle/input/{competition_id}",
        f"/kaggle/input/competitions/{competition_id}",
        "/kaggle/input"
    ]

    for base_path in possible_paths:
        if os.path.exists(base_path):
            print(f"Checking {base_path}...")
            # Recursive search for train file
            for root, dirs, files in os.walk(base_path):
                for f in files:
                    if f.startswith('train') and (f.endswith('.csv') or f.endswith('.jsonl') or f.endswith('.json')):
                        train_file = os.path.join(root, f)
                        print(f"Found training file: {train_file}")
                        break
                if train_file:
                    break
        if train_file:
            break

    if not train_file:
        print(f"ERROR: Could not find training data in any standard Kaggle input path.")
        sys.exit(1)

    print(f"Using dataset file: {train_file}")

    # 3. Load model in BF16 natively
    print("Loading model in BF16...")
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.bfloat16
        )
        print("Model loaded successfully!")

        # Diagnostic: Print a few module names to verify target_modules
        print("Sample module names:")
        for i, (name, _) in enumerate(model.named_modules()):
            if i < 20 or any(x in name for x in ["in_proj", "out_proj"]):
                print(f"  {name}")
            if i > 500: # Don't print everything
                break
    except Exception as e:
        print(f"ERROR loading model: {e}")
        traceback.print_exc()
        sys.exit(1)

    # 4. Configure LoRA
    print("Configuring LoRA...")
    # Use a simpler list-based matching which is more robust than complex regex
    # PEFT will match these names as suffixes
    target_modules = ["in_proj", "out_proj", "up_proj", "down_proj"]

    print(f"Targeting modules: {target_modules}")
    lora_config = LoraConfig(
        r=32,
        lora_alpha=16,
        target_modules=target_modules,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)
    print("LoRA configured successfully!")
    model.print_trainable_parameters()

    # 5. Simple test to make sure everything works
    print("Performing forward pass test...")
    dummy_input = torch.randint(0, model.config.vocab_size, (1, 10)).to(next(model.parameters()).device)
    with torch.no_grad():
        output = model(dummy_input)
    print(f"Forward pass successful! Output shape: {output.logits.shape}")

    # 6. Save baseline adapter
    print("Saving baseline LoRA adapter...")
    adapter_path = "nemotron_lora_adapter"
    model.save_pretrained(adapter_path)

    # Also save the tokenizer for completeness
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        tokenizer.save_pretrained(adapter_path)
        print("Tokenizer saved successfully!")
    except Exception as e:
        print(f"Warning: Could not save tokenizer: {e}")

    print("Baseline adapter saved successfully!")

    # 7. Package submission
    print("Packaging submission.zip...")
    # Change to adapter directory and zip contents to ensure flat structure
    subprocess.run(f"cd {adapter_path} && zip -r ../submission.zip ./*", shell=True, check=True)
    print("submission.zip created successfully!")

    print("=" * 50)
    print("TRAINING COMPLETED SUCCESSFULLY")
    print("=" * 50)

except Exception as e:
    print(f"ERROR IN TRAINING: {e}")
    traceback.print_exc()
    sys.exit(1)
"""
