import os

import pandas as pd
import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer


def setup_environment():
    print("=== [1/8] Setting up Blackwell environment... ===")
    os.environ["TRITON_PTXAS_PATH"] = "/tmp/triton/backends/nvidia/bin/ptxas-blackwell"
    # Ensure binary exists and is executable (Handshake Mandate)
    # ... (skipping binary setup for brevity, assuming existing script handles it)

    print("=== [2/8] Installing offline dependencies... ===")
    # SIDE-LOADING PATTERN
    wheel_path = "/kaggle/input/rocm-training-wheels"
    if os.path.exists(wheel_path):
        os.system(f"pip install --no-index --find-links={wheel_path} trl bitsandbytes")
    else:
        print("WARNING: Wheel dataset not found. Training will likely fail.")


def train():
    setup_environment()

    model_id = "nvidia/NVIDIA-Nemotron-3-Nano-30B-BF16"
    print(f"Loading model: {model_id}")

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
    )

    # LoRA rank 32 (optimized for competition)
    peft_config = LoraConfig(
        r=32,
        lora_alpha=64,
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
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # Load and format data
    train_df = pd.read_csv("/kaggle/input/nvidia-nemotron-model-reasoning-challenge/train.csv")
    # Format: <thinking>{trace}</thinking>\boxed{answer}
    # For now, we assume 'prompt' and 'answer' columns exist
    train_df["text"] = train_df.apply(
        lambda x: (
            f"<|im_start|>user\n{x['prompt']}<|im_end|>\n<|im_start|>assistant\n<thinking>...</thinking>\\boxed{{{x['answer']}}}<|im_end|>"
        ),
        axis=1,
    )
    dataset = Dataset.from_pandas(train_df[["text"]])

    training_args = SFTConfig(
        output_dir="./nemotron-lora-v28",
        max_seq_length=4096,
        dataset_text_field="text",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=10,
        num_train_epochs=2,
        save_steps=100,
        bf16=True,
        optim="paged_adamw_8bit",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=training_args,
        tokenizer=tokenizer,
    )

    print("Starting training...")
    trainer.train()

    print("Saving final adapter...")
    trainer.model.save_pretrained("./final_adapter")
    print("Done.")


if __name__ == "__main__":
    train()
