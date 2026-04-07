"""QLoRA Fine-tuning script for Gemma 4 (Cohezion Specialization).

Uses unsloth for high-performance fine-tuning on the G4 Blackwell/AMD setup.
Specializes the model on Cohezion Knowledge Graph and Unified Physics.
"""

import os
import torch
from datasets import load_dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments

# Configuration
MODEL_NAME = "unsloth/gemma-2-9b-it-bnb-4bit" # Base for specialized tuning
MAX_SEQ_LENGTH = 4096
DATASET_PATH = "data/finetuning/gemma4/cohezion_physics_tek.jsonl"
OUTPUT_DIR = "models/specialized/gemma4-cohezion-v1"

def finetune():
    # 1. Load Model & Tokenizer
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=True,
    )

    # 2. Add LoRA Adapters
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj",],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    # 3. Load Dataset
    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found at {DATASET_PATH}. Please generate it first.")
        return

    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    # 4. Define Trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=5,
            max_steps=60, # Small run for demonstration/hackathon
            learning_rate=2e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=3407,
            output_dir=OUTPUT_DIR,
        ),
    )

    # 5. Execute Training
    trainer.train()

    # 6. Save specialized model
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"Fine-tuning complete. Model saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    finetune()
