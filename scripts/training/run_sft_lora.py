#!/usr/bin/env python3
"""Real SFT + LoRA training script — invoked as a subprocess by PrecipitationOrchestrator.

Usage:
    python scripts/training/run_sft_lora.py \
        --dataset data/training/preferences.jsonl \
        --base-model Qwen/Qwen2.5-0.5B-Instruct \
        --output-dir models/cohezion-gen/gen-0 \
        --lora-r 32 --lora-alpha 64 --epochs 1

Deps: transformers + peft + trl + datasets. If any are missing, the script
writes a marker file and exits 2 so the orchestrator can still record the
attempt without crashing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SFT+LoRA fine-tune on journey-derived data")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--lora-r", type=int, default=32)
    parser.add_argument("--lora-alpha", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-seq-length", type=int, default=512)
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Skip real training; write a marker and exit 0. Useful for CI.",
    )
    return parser.parse_args(argv)


def run_mock(args: argparse.Namespace) -> int:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    marker = args.output_dir / "training.manifest.json"
    marker.write_text(
        json.dumps(
            {
                "mode": "mock",
                "base_model": args.base_model,
                "dataset": str(args.dataset),
                "lora_r": args.lora_r,
                "lora_alpha": args.lora_alpha,
                "epochs": args.epochs,
            },
            indent=2,
        )
    )
    # Simulate a checkpoint file too so callers can find it by path convention.
    (args.output_dir / "lora.safetensors").write_text("mock-checkpoint")
    return 0


def run_real(args: argparse.Namespace) -> int:
    try:
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training  # noqa: F401
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "training.manifest.json").write_text(
            json.dumps(
                {
                    "mode": "unavailable",
                    "reason": f"missing dependency: {exc}",
                    "base_model": args.base_model,
                    "dataset": str(args.dataset),
                },
                indent=2,
            )
        )
        return 2

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForCausalLM.from_pretrained(args.base_model)

    dataset = load_dataset("json", data_files=str(args.dataset), split="train")

    def format_example(example: dict) -> dict:
        return {
            "text": (
                f"[INST] {example['prompt']} [/INST] {example['chosen']}"
                if "chosen" in example and "prompt" in example
                else example.get("text", "")
            )
        }

    dataset = dataset.map(format_example)

    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    sft_config = SFTConfig(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        max_seq_length=args.max_seq_length,
        save_strategy="epoch",
        logging_steps=10,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        peft_config=peft_config,
        args=sft_config,
    )
    trainer.train()
    trainer.save_model(str(args.output_dir))

    (args.output_dir / "training.manifest.json").write_text(
        json.dumps(
            {
                "mode": "real",
                "base_model": args.base_model,
                "dataset": str(args.dataset),
                "lora_r": args.lora_r,
                "lora_alpha": args.lora_alpha,
                "epochs": args.epochs,
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mock:
        return run_mock(args)
    return run_real(args)


if __name__ == "__main__":
    sys.exit(main())
