#!/usr/bin/env python3
"""Train Nemotron LoRA locally and produce submission.zip.

Run on your local machine with Lemonade server (AMD GPU).
The script trains on the full dataset and outputs submission.zip
that can be submitted to Kaggle.
"""

import os
import sys
import zipfile


# Check for pre-installed deps
try:
    import pandas as pd
    import torch
    from datasets import Dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install: pip install torch transformers peft datasets accelerate")
    sys.exit(1)

# ── Configuration ──
TRAIN_CSV = "/tmp/train.csv"  # Download from Kaggle competition
OUTPUT_DIR = "/tmp/nemotron_lora_local"
SUBMISSION_ZIP = "/tmp/submission.zip"


def prepare_training_data():
    """Load and format training examples."""
    print("Loading training data...")
    df = pd.read_csv(TRAIN_CSV)
    print(f"  {len(df)} examples, columns: {list(df.columns)}")

    # Simple formatting: problem + boxed answer
    texts = []
    for _, row in df.iterrows():
        text = f"Problem: {row['prompt']}\n\nLet's solve this step by step.\n\nTherefore, the answer is \\boxed{{{row['answer']}}}."
        texts.append(text)

    print(f"  Prepared {len(texts)} training texts")
    return texts


def load_base_model():
    """Load Nemotron base (from local Lemonade or HuggingFace)."""
    model_id = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
    print(f"Loading {model_id}...")

    # Try Lemonade first
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            trust_remote_code=True,
            gguf_file="",  # Let it auto-resolve
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        print("  Loaded via transformers")
    except Exception as e:
        print(f"  transformers load failed: {e}")
        print("  Trying local path...")
        # Fallback to local GGUF if available
        tokenizer = AutoTokenizer.from_pretrained("/tmp/nemotron_model", trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            "/tmp/nemotron_model",
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
        )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer


def setup_lora(model):
    """Configure LoRA adapter."""
    config = LoraConfig(
        r=32,
        lora_alpha=16,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, config)
    model.print_trainable_parameters()
    return model, config


def train():
    """Main training pipeline."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Data
    texts = prepare_training_data()
    dataset = Dataset.from_dict({"text": texts})

    # 2. Tokenize
    print("Tokenizing...")
    tokenizer = load_base_model()[1]

    def tokenize_fn(examples):
        return tokenizer(examples["text"], truncation=True, max_length=1024, padding="max_length")

    tokenized = dataset.map(tokenize_fn, batched=True, remove_columns=["text"])
    # Add labels for causal LM
    tokenized = tokenized.map(lambda x: {"labels": x["input_ids"]}, batched=True)
    print(f"  Tokenized: {len(tokenized)} examples")

    # 3. Model
    print("\nLoading base model...")
    model, tokenizer = load_base_model()

    print("\nSetting up LoRA...")
    model, lora_config = setup_lora(model)

    # 4. Training args
    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=1e-4,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=10,
        save_strategy="epoch",
        report_to="none",
    )

    # 5. Train
    print("\nTraining...")
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized,
        data_collator=collator,
    )
    trainer.train()

    # 6. Save adapter
    print("\nSaving adapter...")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    # 7. Verify and create submission.zip
    print("\nCreating submission.zip...")
    config_path = os.path.join(OUTPUT_DIR, "adapter_config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"adapter_config.json not found at {config_path}")

    # Find all adapter files
    adapter_files = []
    for root, _dirs, files in os.walk(OUTPUT_DIR):
        for f in files:
            if "adapter" in f.lower():
                adapter_files.append(os.path.join(root, f))

    print(f"  Found adapter files: {len(adapter_files)}")

    with zipfile.ZipFile(SUBMISSION_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath in adapter_files:
            arcname = os.path.relpath(fpath, OUTPUT_DIR)
            zf.write(fpath, arcname)
            print(f"  Added: {arcname}")

    print(f"\n{'=' * 60}")
    print(f"SUBMISSION READY: {SUBMISSION_ZIP}")
    print(f"Size: {os.path.getsize(SUBMISSION_ZIP) / 1024:.1f} KB")
    print(f"{'=' * 60}")

    # Show zip contents
    with zipfile.ZipFile(SUBMISSION_ZIP, "r") as zf:
        print("\nZip contents:")
        for name in zf.namelist():
            print(f"  {name}")


if __name__ == "__main__":
    train()
