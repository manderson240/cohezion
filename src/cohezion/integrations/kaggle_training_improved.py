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
                    "dockerImageVersionId": 31287,
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
import time

print("=" * 60)
print("NEMOTRON LORA TRAINING WITH SFT")
print("Knowledge Distillation from Teacher Model + Blackwell Optimization")
print("=" * 60)

def safe_exit(msg="Execution finished."):
    print(f"\n{msg}")
    # Use os._exit or just finish the script to avoid IPython's buggy traceback handler
    # for SystemExit exceptions in some Kaggle environments.
    return

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
    
    print("  Force-injecting DNS...")
    subprocess.run("echo 'nameserver 8.8.8.8' > /etc/resolv.conf", shell=True)
    subprocess.run("echo 'nameserver 8.8.4.4' >> /etc/resolv.conf", shell=True)
    subprocess.run("echo 'nameserver 1.1.1.1' >> /etc/resolv.conf", shell=True)
    
    def check_dns():
        import socket
        try:
            socket.gethostbyname("pypi.org")
            return True
        except socket.error:
            return False

    if not check_dns():
        print("WARNING: DNS failure still detected even after force-injecting.")

    # Blackwell-specific wheel installation for Mamba/SSM
    print("  Installing pre-built wheels for Mamba/SSM...")
    
    def find_wheels(search_path="/kaggle/input"):
        wheels = []
        for root, _, files in os.walk(search_path):
            for f in files:
                if f.endswith(".whl"):
                    wheels.append(os.path.join(root, f))
        return sorted(wheels)

    all_wheels = find_wheels()
    if all_wheels:
        print(f"    Found {len(all_wheels)} wheels in /kaggle/input")
        # Ensure we install to a writable directory to avoid Errno 30 Read-only file system
        os.makedirs("/tmp/pip_packages", exist_ok=True)
        sys.path.insert(0, "/tmp/pip_packages")
        os.environ["PYTHONPATH"] = f"/tmp/pip_packages:{os.environ.get('PYTHONPATH', '')}"

        for wheel in all_wheels:
            # Skip wheels that tend to conflict with Kaggle's core environment if they are already present
            if "setuptools" in wheel or "six" in wheel or "urllib3" in wheel:
                continue
            print(f"    Installing {os.path.basename(wheel)}...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-q", wheel, "--no-index", "--no-deps", "--target", "/tmp/pip_packages"], check=True)
            except Exception as e:
                print(f"    Failed to install {os.path.basename(wheel)}: {e}")
    else:
        print("    WARNING: No pre-built wheels found. Attempting online install.")

    # Install trl, cutlass and other mandatory packages
    MANDATORY_PACKAGES = ["peft", "accelerate", "trl", "bitsandbytes", "nvidia-cutlass", "cutlass"]
    for pkg in MANDATORY_PACKAGES:
        try:
            # Some packages have different import names
            import_name = pkg.replace("-", "_")
            if pkg == "nvidia-cutlass": import_name = "cutlass"
            __import__(import_name)
            print(f"  {pkg} already installed")
        except ImportError:
            print(f"  Attempting install for {pkg}...")
            # Try multiple times for network reliability
            for attempt in range(3):
                try:
                    subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg, "--target", "/tmp/pip_packages"], check=True)
                    print(f"  Successfully installed {pkg}")
                    break
                except Exception:
                    print(f"  Install attempt {attempt+1} for {pkg} failed. Retrying...")
                    time.sleep(5)
                    if attempt == 1:
                        print("  Force-injecting DNS again...")
                        subprocess.run("echo 'nameserver 8.8.8.8' > /etc/resolv.conf", shell=True)

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
    else:
        print("  WARNING: CUDA NOT AVAILABLE")

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
        print("ERROR: Training data not found. Using dummy data for sanity check.")
        df = pd.DataFrame({
            'prompt': ['What is 2+2?', 'Explain gravity'],
            'answer': ['4', 'Gravity is a force that pulls objects toward each other.']
        })
    else:
        df = pd.read_csv(train_file)
        print(f"  Loaded {len(df)} samples. Columns: {list(df.columns)}")
    
    # Map columns correctly (Competition uses 'prompt' and 'answer')
    PROMPT_COL = 'prompt' if 'prompt' in df.columns else ('question' if 'question' in df.columns else 'problem')
    ANSWER_COL = 'answer'

    # 5. Teacher trace generation (knowledge distillation)
    print("\n[5/8] Generating teacher traces for distillation...")
    teacher_model_name = "deepseek-ai/deepseek-r1-distill-qwen-7b"
    
    try:
        print(f"  Loading teacher: {teacher_model_name}")
        teacher_tokenizer = AutoTokenizer.from_pretrained(teacher_model_name, trust_remote_code=True)
        
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        
        teacher_model = AutoModelForCausalLM.from_pretrained(
            teacher_model_name,
            quantization_config=bnb_config,
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

        sample_size = min(50, len(df)) # Reduced sample size for reliability
        print(f"  Generating traces for {sample_size} samples...")
        filtered_data = []
        for idx in range(sample_size):
            row = df.iloc[idx]
            try:
                trace = generate_teacher_trace(row)
                filtered_data.append({
                    'prompt': row[PROMPT_COL],
                    'answer': row[ANSWER_COL],
                    'teacher_trace': trace
                })
            except Exception as e:
                print(f"    Failed trace for sample {idx}: {e}")
                
            if (idx + 1) % 10 == 0: print(f"    Generated {idx + 1}/{sample_size}")

        del teacher_model
        gc.collect()
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"  Teacher generation failed: {e}. Falling back to ground truth.")
        filtered_data = []
        for _, row in df.head(100).iterrows():
            filtered_data.append({
                'prompt': row[PROMPT_COL],
                'answer': row[ANSWER_COL],
                'teacher_trace': ''
            })

    # 6. Load student model
    print("\n[6/8] Loading student model...")
    model_id = "metric/nemotron-3-nano-30b-a3b-bf16/transformers/default"
    model_path = kagglehub.model_download(model_id)
    if not model_path:
        print(f"ERROR: Failed to download model {model_id}")
        safe_exit("Model download failed")
        
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token
    
    student_bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        model_path, 
        quantization_config=student_bnb_config,
        device_map="auto", 
        trust_remote_code=True
    )
    model = prepare_model_for_kbit_training(model)
    
    lora_config = LoraConfig(
        r=32, lora_alpha=16, 
        target_modules=["in_proj", "out_proj", "up_proj", "down_proj"],
        lora_dropout=0.05, bias="none", task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)

    # 7. Prepare dataset
    print("\n[7/8] Preparing dataset...")
    def format_example(example):
        if example.get('teacher_trace'):
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
        report_to="none",
        save_total_limit=1,
    )

    trainer = SFTTrainer(
        model=model, 
        tokenizer=tokenizer, 
        train_dataset=dataset['train'], 
        eval_dataset=dataset['test'], 
        args=training_args, 
        max_seq_length=1024,
        dataset_text_field="text"
    )
    trainer.train()

    # Save
    trainer.save_model("./nemotron_lora_adapter")
    tokenizer.save_pretrained("./nemotron_lora_adapter")
    subprocess.run("cd nemotron_lora_adapter && zip -r ../submission.zip ./*", shell=True, check=True)
    print("\n" + "=" * 60 + "\nSUBMISSION READY: submission.zip\n" + "=" * 60)

except Exception as e:
    print("\n" + "!" * 60)
    print(f"CRITICAL ERROR: {e}")
    print("!" * 60)
    traceback.print_exc()
    print("\nExiting training script early due to error.")

safe_exit()
"""

