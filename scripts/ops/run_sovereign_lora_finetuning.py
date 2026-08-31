#!/usr/bin/env python3
"""Sovereign Local LoRA Fine-Tuning Pipeline with Dynamic OOM Guard & EventBus Telemetry.

Performs real gradient-descent fine-tuning on Cohezion's verified instruction corpus:
1. Validates dynamic memory floor via `OOMGuard.get_memory_state()`.
2. Emits start, epoch progress, and completion events over `EventBus`.
3. Trains a LoRA rank-16 adapter with PyTorch and PEFT.
4. Exports genuine `.safetensors` adapter weights and model config.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(REPO_ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sovereign_finetuning")

from cohezion.core.event_bus import Event, EventBus, get_event_bus
from cohezion.reliability.oom_guard import OOMGuard

CORPUS_FILE = REPO_ROOT / "data/cohezion_master_10k_finetuning_corpus.jsonl"
OUTPUT_DIR = REPO_ROOT / "checkpoints/cohezion_lora_drafter_adapter"


def get_cached_base_model() -> str:
    """Finds cached base model path in HuggingFace cache or defaults to Qwen."""
    hf_hub = Path.home() / ".cache" / "huggingface" / "hub"
    candidate_dirs = [
        "models--Qwen--Qwen2.5-0.5B-Instruct",
        "models--Qwen--Qwen2.5-1.5B-Instruct",
        "models--Qwen--Qwen2.5-Coder-0.5B",
        "models--google--gemma-2-2b-it",
    ]
    for c in candidate_dirs:
        p = hf_hub / c / "snapshots"
        if p.exists():
            snaps = list(p.iterdir())
            if snaps:
                return str(snaps[0])
    return "Qwen/Qwen2.5-0.5B-Instruct"


def load_dataset(max_samples: int = 150):
    from datasets import Dataset
    data = []
    if not CORPUS_FILE.exists():
        raise FileNotFoundError(f"Corpus file not found: {CORPUS_FILE}")

    with open(CORPUS_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if idx >= max_samples:
                break
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            prompt = f"<|im_start|>user\n{item['instruction']}<|im_end|>\n<|im_start|>assistant\n{item['response']}<|im_end|>"
            data.append({"text": prompt})
    logger.info("Loaded %d high-quality verified samples for Sprint 1 LoRA training.", len(data))
    return Dataset.from_list(data)


async def execute_finetuning(num_samples: int = 100, epochs: int = 1, batch_size: int = 2):
    bus = await get_event_bus()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Preflight Memory Check via OOMGuard
    mem = OOMGuard.get_memory_state()
    logger.info("Preflight Memory Check: Available=%.2f GiB, Total=%.2f GiB, Floor=%.2f GiB, Safe=%s", mem.available_gb, mem.total_gb, mem.dynamic_floor_gb, mem.is_safe)
    
    if not mem.is_safe or mem.available_gb < 15.0:
        logger.error("Aborting fine-tuning: Insufficient memory headroom (%.2f GiB available).", mem.available_gb)
        await bus.publish(Event(
            type="training_aborted",
            source="sovereign_finetuning",
            payload={"reason": "OOMGuard unsafe memory floor", "available_gb": mem.available_gb},
        ))
        return False

    # 2. Publish Training Start Event
    base_model_path = get_cached_base_model()
    await bus.publish(Event(
        type="training_started",
        source="sovereign_finetuning",
        payload={
            "base_model": base_model_path,
            "num_samples": num_samples,
            "epochs": epochs,
            "batch_size": batch_size,
            "available_ram_gb": mem.available_gb,
        },
    ))
    logger.info("🚀 Published `training_started` event to EventBus.")

    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
    )
    from peft import LoraConfig, get_peft_model, TaskType

    # Explicitly use CPU device on Zen 4 to prevent CUDA/HIP aperture segmentation faults
    device = "cpu"
    logger.info("Loading Tokenizer and Base Model on device: %s (16-core Zen 4 AVX-512)...", device)

    base_model_name = "Qwen/Qwen2.5-0.5B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
    )

    # Configure LoRA
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)
    trainable_params, all_params = model.get_nb_trainable_parameters()
    logger.info("LoRA Configured: %d trainable params / %d total params (%.3f%%)", trainable_params, all_params, 100 * trainable_params / all_params)

    dataset = load_dataset(max_samples=num_samples)

    def tokenize_fn(examples):
        return tokenizer(examples["text"], truncation=True, max_length=512, padding="max_length")

    tokenized_dataset = dataset.map(tokenize_fn, batched=True, remove_columns=["text"])

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR / "tmp_checkpoints"),
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=2,
        num_train_epochs=epochs,
        learning_rate=3e-4,
        logging_steps=5,
        save_strategy="no",
        report_to="none",
        use_cpu=(device == "cpu"),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    logger.info("Executing training loop across %d steps...", len(tokenized_dataset) // (batch_size * 2))
    t0 = time.perf_counter()
    train_result = trainer.train()
    elapsed_s = time.perf_counter() - t0

    # Save real adapter weights
    model.save_pretrained(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))

    loss = train_result.training_loss
    logger.info("✅ Fine-Tuning Complete! Loss: %.4f | Time: %.2fs | Saved to %s", loss, elapsed_s, OUTPUT_DIR)

    # 3. Publish Training Complete Event
    await bus.publish(Event(
        type="training_completed",
        source="sovereign_finetuning",
        payload={
            "output_dir": str(OUTPUT_DIR),
            "final_loss": round(loss, 4),
            "elapsed_seconds": round(elapsed_s, 2),
            "trainable_params": trainable_params,
        },
    ))
    logger.info("🚀 Published `training_completed` event to EventBus.")
    return True


if __name__ == "__main__":
    asyncio.run(execute_finetuning())
