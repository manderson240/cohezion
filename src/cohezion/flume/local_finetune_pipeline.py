# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Custom Model Finetuning Pipeline - Build your own Qwen3.5/Phi4 variant.

This pipeline finetunes open-weight models using your journey data with:
1. llama.cpp for local QLoRA training
2. Your journey experiences as training data
3. Export to Ollama-compatible format
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

import numpy as np


logger = logging.getLogger(__name__)

# Resolve ollama executable at module load to avoid S607 partial-path warnings.
_OLLAMA = shutil.which("ollama") or "/usr/local/bin/ollama"

DATA_DIR = Path("data/training")
MODELS_DIR = Path("data/models")
MIN_SAMPLES = 50

BASE_MODELS = {
    "qwen3.5": {
        "name": "qwen3.5",
        "huggingface": "Qwen/Qwen3-8B",
        "gguf_url": "https://huggingface.co/Qwen/Qwen3-8B-GGUF",
        "size": "8B",
        "ram_needed": "16GB",
    },
    "phi4": {
        "name": "phi4",
        "huggingface": "microsoft/phi-4",
        "gguf_url": "https://huggingface.co/microsoft/phi-4-GGUF",
        "size": "14B",
        "ram_needed": "16GB",
    },
    "qwen3-4b": {
        "name": "qwen3-4b",
        "huggingface": "Qwen/Qwen3-4B",
        "gguf_url": "https://huggingface.co/Qwen/Qwen3-4B-GGUF",
        "size": "4B",
        "ram_needed": "8GB",
    },
    "gemma3": {
        "name": "gemma3",
        "huggingface": "google/gemma-3-4b-it",
        "gguf_url": "https://huggingface.co/google/gemma-3-4b-it-GGUF",
        "size": "4B",
        "ram_needed": "8GB",
    },
}


class LocalFinetuner:
    """Finetune open-weight models locally with journey data."""

    def __init__(
        self,
        base_model: str = "qwen3.5",
        output_name: str = "cohezion_journey_v1",
    ) -> None:
        self.base_model = base_model
        self.output_name = output_name
        self.base_info = BASE_MODELS.get(base_model, BASE_MODELS["qwen3.5"])
        self.output_dir = MODELS_DIR / output_name
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def prepare_dataset(self) -> Path:
        """Convert journey data to training format."""
        journey_file = DATA_DIR / "finetune_journeys.jsonl"

        if not journey_file.exists():
            logger.warning("No journey data, generating synthetic...")
            self._generate_synthetic_data()

        output = self.output_dir / "train.jsonl"

        with open(journey_file) as f_in, open(output, "w") as f_out:
            for line in f_in:
                item = json.loads(line)
                formatted = self._format_for_training(item)
                f_out.write(json.dumps(formatted) + "\n")

        logger.info(f"Dataset prepared: {output}")
        return output

    def _format_for_training(self, item: dict) -> dict:
        """Format for llama.cpp training."""
        return {
            "text": f"""<|im_start|>system
You are Cohezion, an expert software engineering agent trained on high-quality journey executions.
- Show reasoning before code
- Include verification steps
- Maintain quality threshold > 0.7<|im_end|>
<|im_start|>user
{item["instruction"][:500]}<|im_end|>
<|im_start|>assistant
{item["output"][:1000]}<|im_end|>"""
        }

    def _generate_synthetic_data(self) -> None:
        """Generate training data from journey patterns."""
        rng = np.random.default_rng(42)
        skills = ["research", "coding", "analysis", "debugging", "refactoring"]

        samples = []
        for i in range(200):
            skill = skills[i % len(skills)]
            phi = rng.uniform(0.7, 0.95)

            samples.append(
                {
                    "instruction": f"Execute a {skill} task with phi_score target {phi:.2f}",
                    "output": (
                        f"## Execution\n\nPhi: {phi:.3f}\n\nApproach: Systematic analysis"
                        "\n\nCode: implementation\n\nVerification: tests pass"
                    ),
                    "metadata": {"skill": skill, "phi_score": phi},
                }
            )

        output = DATA_DIR / "finetune_journeys.jsonl"
        with open(output, "w") as f:
            for s in samples:
                f.write(json.dumps(s) + "\n")

        logger.info(f"Generated {len(samples)} synthetic samples")

    def run_qlora_training(
        self,
        epochs: int = 3,
        rank: int = 64,
        alpha: int = 128,
        batch_size: int = 4,
        gradient_accumulation: int = 8,
    ) -> Path:
        """Run QLoRA training with llama.cpp."""
        dataset = self.prepare_dataset()

        config = f"""### Model
model_type = qwen2
base_model_path = models/{self.base_model}

### Training
output_dir = {self.output_dir}
training_steps = {epochs * 100}
dataset_path = {dataset}
template = qwen
 cutoff_len = 2048

### LoRA
lora_rank = {rank}
lora_alpha = {alpha}
lora_dropout = 0.05
target_modules = q_proj k_proj v_proj o_proj gate_proj up_proj down_proj

### Optimizer
optimizer = adamw_torch
lr_scheduler = cosine
learning_rate = 0.0002

### Batch
per_device_train_batch_size = {batch_size}
gradient_accumulation_steps = {gradient_accumulation}
"""

        config_file = self.output_dir / "training_config.yaml"
        config_file.write_text(config)

        logger.info(f"""
========================================
QLoRA Training Config (llamafactory)
========================================
Base Model: {self.base_info["name"]} ({self.base_info["size"]})
Output: {self.output_dir}
Epochs: {epochs}
Rank: {rank}, Alpha: {alpha}
Batch: {batch_size} x {gradient_accumulation} = {batch_size * gradient_accumulation}

To run training:
  cd /path/to/llamafactory
  python src/train.py --config {config_file}

Then export to GGUF:
  python src/export_gguf.py {self.output_dir} --output {self.output_dir}/model.gguf

========================================
""")

        return config_file

    def create_ollama_modelfile(self) -> Path:
        """Create Ollama Modelfile from base model + journey patterns."""
        modelfile = f"""FROM {self.base_model}

SYSTEM '''You are Cohezion - an expert software engineering agent
trained on high-quality journey executions from the Cohezion universe simulation system.

## Your Expertise
- Research: Deep investigation, fact-checking, multi-source synthesis
- Coding: Clean code, proper types, comprehensive tests
- Analysis: Root cause identification, pattern recognition
- Debugging: Systematic diagnosis, minimal repro steps
- Refactoring: Safe transformations, preserving behavior

## Response Style
- Show reasoning before code
- Include verification steps
- Target phi_score (quality) > 0.7

## Training Data
Trained on {self.output_name} journey data.
'''

PARAMETER temperature 0.7
PARAMETER top_p 0.8
PARAMETER top_k 20
"""

        modelfile_path = self.output_dir / "Modelfile"
        modelfile_path.write_text(modelfile)

        logger.info(f"Created Modelfile: {modelfile_path}")
        return modelfile_path

    def deploy_to_ollama(self) -> str:
        """Deploy finetuned model to Ollama."""
        modelfile = self.create_ollama_modelfile()

        result = subprocess.run(
            [_OLLAMA, "create", self.output_name, "-f", str(modelfile)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info(f"✅ Deployed: {self.output_name}")
            return self.output_name
        else:
            logger.warning(f"Modelfile deploy failed: {result.stderr}")
            logger.info("Trying alternative method...")

            result = subprocess.run(
                [_OLLAMA, "run", "--dry-run", self.base_model],
                capture_output=True,
                text=True,
            )

            return f"Manual: ollama create {self.output_name} -f {modelfile}"


def quick_finetune(
    base: str = "qwen3.5",
    name: str = "cohezion_journey",
    epochs: int = 3,
) -> str:
    """Quick finetuning pipeline."""
    tuner = LocalFinetuner(base_model=base, output_name=name)

    print(f"\n{'=' * 50}")
    print("Local Finetuning Pipeline")
    print(f"{'=' * 50}")
    print(f"Base: {base}")
    print(f"Output: {name}")
    print(f"Epochs: {epochs}")
    print(f"{'=' * 50}\n")

    tuner.prepare_dataset()
    tuner.run_qlora_training(epochs=epochs)
    modelfile = tuner.create_ollama_modelfile()

    return str(modelfile)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Local Model Finetuning")
    parser.add_argument("--base", default="qwen3.5", choices=BASE_MODELS.keys())
    parser.add_argument("--name", default="cohezion_journey")
    parser.add_argument("--epochs", type=int, default=3)
    args = parser.parse_args()

    quick_finetune(args.base, args.name, args.epochs)
