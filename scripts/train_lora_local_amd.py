#!/usr/bin/env python3
"""
Local LoRA Trainer for AMD Strix Halo (RDNA3.5 iGPU)
No Kaggle dependency — runs entirely locally.
Uses transformers + peft + torch (ROCm) automatically.
Targets gemma-4-4b for Nemotron Reasoning Challenge submission.
"""

import json
import os
import sys
import warnings


warnings.filterwarnings("ignore")

# =========================================
# CONFIGURATION
# =========================================
TRAIN_CSV = "/home/mike-anderson/dev/cohezion/data/nemotron/train.csv"
TEST_CSV = "/home/mike-anderson/dev/cohezion/data/nemotron/test.csv"
OUTPUT_DIR = "/home/mike-anderson/dev/cohezion/models/nemotron-lora-local"
SUBMISSION_ZIP = "/home/mike-anderson/dev/cohezion/submission-local.zip"

MODEL_NAME = "unsloth/gemma-4-4b-it"  # Kaggle compatible ID
LORA_RANK = 32
LORA_ALPHA = 64
LORA_DROPOUT = 0.05
BATCH_SIZE = 1
GRAD_ACCUM = 8
EPOCHS = 1
MAX_SEQ_LEN = 512
LEARNING_RATE = 2e-4

# =========================================
# PATH DETECTION (works on any OS)
# =========================================
def find_file(name, root="/home/mike-anderson/dev"):
    for dirpath, _, filenames in os.walk(root):
        if name in filenames:
            return os.path.join(dirpath, name)
    return None

train_path = find_file("train.csv")
test_path = find_file("test.csv")
if train_path: TRAIN_CSV = train_path
if test_path: TEST_CSV = test_path
print(f"Train: {TRAIN_CSV}")
print(f"Test:  {TEST_CSV}")

# =========================================
# IMPORTS
# =========================================
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
    print("Install: pip install torch transformers peft datasets pandas")
    sys.exit(1)

# ROCm / device detection
if torch.cuda.is_available():
    device = torch.device("cuda")
    print(f"CUDA: {torch.cuda.get_device_name(0)}")
elif hasattr(torch, "hip") and torch.hip.is_available():
    device = torch.device("hip")
    print("ROCm/HIP detected")
else:
    device = torch.device("cpu")
    print("CPU fallback")

# =========================================
# LOAD DATA
# =========================================
train_df = pd.read_csv(TRAIN_CSV)
print(f"Loaded {len(train_df)} training rows")

# =========================================
# FORMAT: Problem -> Therefore, answer is \boxed{answer}.
# =========================================
def format_example(row):
    prompt = f"Problem: {row['problem']}\n\nTherefore, answer is "
    answer = str(row["answer"])
    return prompt + answer + "."

train_texts = train_df.apply(format_example, axis=1).tolist()
print(f"Prepared {len(train_texts)} training texts")

# =========================================
# TOKENIZER & MODEL (causal LM, no SFTTrainer)
# =========================================
print(f"Loading {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

# Gemma uses "gate_proj" not "gate_up_proj"
lora_config = LoraConfig(
    r=LORA_RANK,
    lora_alpha=LORA_ALPHA,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# =========================================
# DATASET & TRAINING (causal LM, labels = input_ids)
# =========================================
dataset = Dataset.from_dict({"text": train_texts})

def tokenize(batch):
    out = tokenizer(
        batch["text"],
        truncation=True,
        padding="max_length",
        max_length=MAX_SEQ_LEN,
        return_tensors=None,
    )
    out["labels"] = out["input_ids"].copy()
    return out

tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM,
    learning_rate=LEARNING_RATE,
    bf16=torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False,
    logging_steps=50,
    save_strategy="epoch",
    remove_unused_columns=False,
    dataloader_num_workers=0,
    report_to=["none"],
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)

print("Training...")
trainer.train()

# =========================================
# SAVE ADAPTER
# =========================================
model.save_pretrained(os.path.join(OUTPUT_DIR, "adapter"))
tokenizer.save_pretrained(os.path.join(OUTPUT_DIR, "adapter"))

# adapter_config.json
with open(os.path.join(OUTPUT_DIR, "adapter", "adapter_config.json")) as f:
    cfg = json.load(f)
cfg["base_model_name_or_path"] = MODEL_NAME
with open(os.path.join(OUTPUT_DIR, "adapter", "adapter_config.json"), "w") as f:
    json.dump(cfg, f, indent=2)

# =========================================
# SUBMISSION ZIP
# =========================================
import zipfile


with zipfile.ZipFile(SUBMISSION_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
    for fn in ["adapter_config.json", "adapter_model.safetensors"]:
        p = os.path.join(OUTPUT_DIR, "adapter", fn)
        if os.path.exists(p):
            zf.write(p, arcname=fn)
            print(f"Added {fn}")

print("\\n=== SUBMISSION READY ===")
print(f"File: {SUBMISSION_ZIP}")
print(f"To submit: kaggle competitions submit -c nvidia-nemotron-model-reasoning-challenge -f {SUBMISSION_ZIP} -m 'Local AMD training'")

# Quick size check
size_mb = os.path.getsize(SUBMISSION_ZIP) / 1024 / 1024
print(f"Size: {size_mb:.1f} MB")
