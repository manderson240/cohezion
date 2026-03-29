import csv
import json
import logging
from pathlib import Path

from cohezion.flume.vae_encoder import get_encoder


logger = logging.getLogger(__name__)


class KaggleCurator:
    """
    Curates and processes Kaggle datasets using FLUME VAE for embeddings
    and formatting data for LoRA fine-tuning.

    Supports both JSONL and CSV formats.
    """

    def __init__(self):
        self.encoder = get_encoder()

    async def process_dataset(self, input_path: Path, output_path: Path) -> None:
        """
        Process a dataset (CSV or JSONL), adding semantic embeddings for each item.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        processed_data = []

        if input_path.suffix == ".csv":
            with open(input_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # NVIDIA Nemotron uses 'prompt' and 'answer'
                    question = row.get("prompt") or row.get("question", "")
                    answer = row.get("answer", "")
                    text_to_encode = f"{question} {answer}"
                    row["embedding"] = self.encoder.encode(text_to_encode).tolist()
                    processed_data.append(row)
        else:
            # Assume JSONL
            with open(input_path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    question = item.get("prompt") or item.get("question", "")
                    answer = item.get("answer", "")
                    text_to_encode = f"{question} {answer}"
                    item["embedding"] = self.encoder.encode(text_to_encode).tolist()
                    processed_data.append(item)

        with open(output_path, "w", encoding="utf-8") as f:
            for item in processed_data:
                f.write(json.dumps(item) + "\n")

        logger.info(f"Processed {len(processed_data)} items and saved to {output_path}")

    def prepare_finetuning_data(self, input_path: Path, output_path: Path) -> None:
        """
        Convert a raw dataset into the format expected by LoRA fine-tuning scripts,
        ensuring the answer is wrapped in \boxed{}.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        finetune_data = []

        if input_path.suffix == ".csv":
            with open(input_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    question = row.get("prompt") or row.get("question", "")
                    answer = row.get("answer", "")
                    finetune_item = {
                        "instruction": f"Solve the following reasoning problem: {question}",
                        "output": f"The final answer is \\boxed{{{answer}}}",
                    }
                    finetune_data.append(finetune_item)
        else:
            with open(input_path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    question = item.get("prompt") or item.get("question", "")
                    answer = item.get("answer", "")
                    finetune_item = {
                        "instruction": f"Solve the following reasoning problem: {question}",
                        "output": f"The final answer is \\boxed{{{answer}}}",
                    }
                    finetune_data.append(finetune_item)

        with open(output_path, "w", encoding="utf-8") as f:
            for item in finetune_data:
                f.write(json.dumps(item) + "\n")

        logger.info(f"Prepared {len(finetune_data)} items for fine-tuning at {output_path}")
