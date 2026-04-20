import os

import torch
import trackio
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer


# 1. Environment Setup
os.environ["TOKENIZERS_PARALLELISM"] = "false"
PROJECT_NAME = "cohezion-axiomatic-brain"
MODEL_ID = "Qwen/Qwen3-1.7B"  # Scaled back model
DATASET_PATH = "cohezion_kb.jsonl"


def train():
    # 2. Initialize Trackio
    trackio.init(project=PROJECT_NAME, run_name="local-qwen3-1.7b-sft-breathable")

    # 3. Load Dataset
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

    # 4. Model & Tokenizer (Optimized for AMD/ROCm)
    print(f"🚀 Loading base model: {MODEL_ID}")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    # 5. PEFT Configuration (Reduced Intensity)
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # 6. Training Arguments (Breathable)
    training_args = SFTConfig(
        output_dir="./output/qwen3-1.7b-cohezion",
        max_length=1024,
        dataset_text_field="output",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=1e-4,
        lr_scheduler_type="cosine",
        num_train_epochs=1,
        weight_decay=0.01,
        save_strategy="no",
        logging_steps=5,
        push_to_hub=False,
        report_to="trackio",
        bf16=True,
        gradient_checkpointing=True,
    )

    # 7. SFT Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        args=training_args,
        tokenizer=tokenizer,
    )

    print("🧠 Starting Breathable Fine-Tuning...")
    trainer.train()

    # 8. Save Artifacts
    trainer.save_model("./output/qwen3-1.7b-cohezion-final")
    print("✅ Training Complete. Model saved to ./output/qwen3-1.7b-cohezion-final")
    trackio.finish()


if __name__ == "__main__":
    train()
