import os

import pandas as pd
import torch
from datasets import Dataset


def setup_environment():
    print("=== [1/8] Setting up Blackwell environment... ===")
    os.environ["TRITON_PTXAS_PATH"] = "/tmp/triton/backends/nvidia/bin/ptxas-blackwell"

    print("=== [2/8] Installing offline dependencies... ===")
    print("Listing /kaggle/input contents:")
    for root, dirs, files in os.walk("/kaggle/input"):
        for file in files:
            print(f"  {os.path.join(root, file)}")

    found_wheels = []
    for root, dirs, files in os.walk("/kaggle/input"):
        for file in files:
            if file.endswith(".whl"):
                found_wheels.append(root)
                break

    if found_wheels:
        print(f"Found {len(found_wheels)} wheel directories. Installing sequentially...")
        for path in set(found_wheels):
            print(f"Installing from: {path}")
            os.system(
                f"pip install --no-index --find-links='{path}' causal-conv1d mamba-ssm trl bitsandbytes peft transformers"
            )
        if res != 0:
            print("ERROR: Offline installation failed.")
    else:
        print("WARNING: No wheel files found in /kaggle/input. Attempting online install.")
        os.system("pip install trl bitsandbytes")


def train():
    setup_environment()

    # Delayed imports to survive setup phase
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    print("Searching for model config.json...")
    model_path = None
    for root, dirs, files in os.walk("/kaggle/input"):
        if "config.json" in files:
            model_path = root
            print(f"Found model config at: {model_path}")
            break

    if not model_path:
        print("CRITICAL: model config not found. Using remote ID.")
        model_path = "nvidia/NVIDIA-Nemotron-3-Nano-30B-BF16"

    print(f"Loading tokenizer from {model_path}...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    print(f"Loading model from {model_path}...")
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
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
    train_path = "/kaggle/input/nvidia-nemotron-model-reasoning-challenge/train.csv"
    trace_path = "train_with_traces.csv"

    if os.path.exists(trace_path):
        print(f"Loading generated traces from {trace_path}...")
        train_df = pd.read_csv(trace_path)
        if "text" in train_df.columns:
            dataset = Dataset.from_pandas(train_df[["text"]])
        else:
            train_df["text"] = train_df.apply(
                lambda x: (
                    f"<|im_start|>user\n{x['prompt']}<|im_end|>\n<|im_start|>assistant\n<thinking>{x.get('reasoning_trace', '...')}</thinking>\\boxed{{{x['answer']}}}<|im_end|>"
                ),
                axis=1,
            )
            dataset = Dataset.from_pandas(train_df[["text"]])
    elif os.path.exists(train_path):
        print(f"Loading base dataset from {train_path}...")
        train_df = pd.read_csv(train_path)
        train_df["text"] = train_df.apply(
            lambda x: (
                f"<|im_start|>user\n{x['prompt']}<|im_end|>\n<|im_start|>assistant\n<thinking>...</thinking>\\boxed{{{x['answer']}}}<|im_end|>"
            ),
            axis=1,
        )
        dataset = Dataset.from_pandas(train_df[["text"]])
    else:
        print("Mocking dataset for dry-run...")
        dataset = Dataset.from_dict(
            {
                "text": [
                    "<|im_start|>user\n2+2\n<|im_end|>\n<|im_start|>assistant\n<thinking>4</thinking>\\boxed{4}<|im_end|>"
                ]
            }
        )

    training_args = SFTConfig(
        output_dir="./nemotron-lora-v29",
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

    # Robust verification
    if os.path.exists("./final_adapter/adapter_config.json"):
        print("=== SUCCESS: Final adapter saved to ./final_adapter ===")
    else:
        print("=== ERROR: Adapter save verification failed. Check permissions/disk space. ===")
    print("Done.")


if __name__ == "__main__":
    train()
