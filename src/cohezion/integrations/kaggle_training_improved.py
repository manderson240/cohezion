# ruff: noqa: E501  # long lines: SQL/URLs/docstrings — wrapping reduces readability
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
        self,
        r: int = 8,
        alpha: int = 16,
        dropout: float = 0.05,
        target_modules: list[str] | None = None,
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
        Improved version with Blackwell fix and teacher distillation.
        """
        return r"""
import os
import subprocess
import sys
import traceback
import json
import gc

print("=" * 60)
print("NEMOTRON LORA TRAINING WITH SFT")
print("Knowledge Distillation from Teacher Model + Blackwell Optimization")
print("=" * 60)

try:
    # 1. Blackwell Environment Setup
    print("\n[1/8] Setting up Blackwell environment...")
    UTILITY_PATH = "/kaggle/usr/lib/notebooks/ryanholbrook/nvidia_utility_script"
    if os.path.exists(UTILITY_PATH):
        subprocess.run(f"tar -cf - -C {UTILITY_PATH} . | tar -xf - -C /tmp", shell=True, check=True)
        for binary in ["ptxas", "ptxas-blackwell"]:
            bin_path = f"/tmp/triton/backends/nvidia/bin/{binary}"
            if os.path.exists(bin_path):
                subprocess.run(f"chmod +x {bin_path}", shell=True, check=True)
        os.environ["TRITON_PTXAS_PATH"] = "/tmp/triton/backends/nvidia/bin/ptxas-blackwell"
        sys.path.insert(0, "/tmp")
        print("Blackwell environment initialized")
    else:
        print(f"WARNING: Utility script not found")

    # 2. Imports & Dependencies
    print("\n[2/8] Loading dependencies...")
    MANDATORY_PACKAGES = ["trl", "peft", "bitsandbytes", "accelerate", "nvidia-cutlass", "mamba_ssm", "causal_conv1d"]
    for pkg in MANDATORY_PACKAGES:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  {pkg} already installed")
        except ImportError:
            print(f"  Installing {pkg}...")
            # Try standard install first
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])
            except:
                print(f"  Standard install failed for {pkg}, trying with --no-build-isolation...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--no-build-isolation", pkg])

    import torch
    import pandas as pd
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from datasets import Dataset
    from trl import SFTTrainer
    import kagglehub

    # 3. Hardware check
    print(f"\n[3/8] Hardware configuration:")
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            prop = torch.cuda.get_device_properties(i)
            print(f"  GPU {i}: {prop.name} ({prop.total_memory / 1024**3:.1f} GB)")

    # 4. Load competition data
    print("\n[4/8] Loading training data...")
    competition_id = "nvidia-nemotron-model-reasoning-challenge"
    train_file = None
    for base_path in [f"/kaggle/input/{competition_id}", "/kaggle/input"]:
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for f in files:
                    if 'train' in f.lower() and f.endswith('.csv'):
                        train_file = os.path.join(root, f)
                        break
                if train_file: break
        if train_file: break

    if not train_file:
        print("ERROR: Training data not found")
        sys.exit(1)

    df = pd.read_csv(train_file)
    print(f"  Columns: {list(df.columns)}")

    # Map columns correctly (Competition uses 'prompt' and 'answer')
    PROMPT_COL = 'prompt' if 'prompt' in df.columns else ('question' if 'question' in df.columns else 'problem')
    ANSWER_COL = 'answer'

    # 5. Teacher trace generation (knowledge distillation)
    print("\n[5/8] Generating teacher traces for distillation...")
    teacher_model_name = "deepseek-ai/deepseek-r1-distill-qwen-32b"

    try:
        print(f"  Loading teacher: {teacher_model_name}")
        teacher_tokenizer = AutoTokenizer.from_pretrained(teacher_model_name, trust_remote_code=True)
        teacher_model = AutoModelForCausalLM.from_pretrained(
            teacher_model_name,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )

        def generate_teacher_trace(row):
            prompt = f"Solve this step by step and put your final answer in \\boxed{{}}.\n\nProblem: {row[PROMPT_COL]}\n\nLet's think through this carefully:"
            inputs = teacher_tokenizer(prompt, return_tensors="pt").to(teacher_model.device)
            with torch.no_grad():
                outputs = teacher_model.generate(**inputs, max_new_tokens=512, temperature=0.7, do_sample=True)
            response = teacher_tokenizer.decode(outputs[0], skip_special_tokens=True)
            return response[len(prompt):].strip()

        sample_size = min(50, len(df))
        print(f"  Generating traces for {sample_size} samples...")
        filtered_data = []
        for idx in range(sample_size):
            row = df.iloc[idx]
            trace = generate_teacher_trace(row)
            filtered_data.append({
                'prompt': row[PROMPT_COL],
                'answer': row[ANSWER_COL],
                'teacher_trace': trace
            })
            if (idx + 1) % 10 == 0: print(f"    Generated {idx + 1}/{sample_size}")

        del teacher_model
        gc.collect()
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"  Teacher generation failed: {e}. Falling back to ground truth.")
        filtered_data = [{'prompt': row[PROMPT_COL], 'answer': row[ANSWER_COL], 'teacher_trace': ''} for _, row in df.head(100).iterrows()]

    # 6. Load student model
    print("\n[6/8] Loading student model...")
    model_path = kagglehub.model_download("metric/nemotron-3-nano-30b-a3b-bf16/transformers/default")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(model_path, device_map="auto", trust_remote_code=True, torch_dtype=torch.bfloat16)

    lora_config = LoraConfig(
        r=32, lora_alpha=16,
        target_modules=["in_proj", "out_proj", "up_proj", "down_proj"],
        lora_dropout=0.05, bias="none", task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)

    # 7. Prepare dataset
    print("\n[7/8] Preparing dataset...")
    def format_example(example):
        if example['teacher_trace']:
            text = f"Problem: {example['prompt']}\n\nSolution:\n{example['teacher_trace']}"
        else:
            text = f"Problem: {example['prompt']}\n\nAnswer: {example['answer']}"
        return {"text": text}

    dataset = Dataset.from_list(filtered_data).map(format_example)
    dataset = dataset.train_test_split(test_size=0.1)

    # 8. Training
    print("\n[8/8] Starting SFT training...")
    training_args = TrainingArguments(
        output_dir="./nemotron_lora_adapter",
        num_train_epochs=1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=1e-4,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=5,
        report_to="none"
    )

    trainer = SFTTrainer(model=model, tokenizer=tokenizer, train_dataset=dataset['train'], eval_dataset=dataset['test'], args=training_args, max_seq_length=1024)
    trainer.train()

    # Save
    trainer.save_model("./nemotron_lora_adapter")
    tokenizer.save_pretrained("./nemotron_lora_adapter")
    subprocess.run("cd nemotron_lora_adapter && zip -r ../submission.zip ./*", shell=True, check=True)
    print("\n" + "=" * 60 + "\nSUBMISSION READY: submission.zip\n" + "=" * 60)

except Exception as e:
    print(f"\nERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
"""
