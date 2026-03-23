import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from cohezion.flume.vae_encoder import get_encoder

logger = logging.getLogger(__name__)

class KaggleCurator:
    """
    Curates and processes Kaggle datasets using FLUME VAE for embeddings
    and formatting data for LoRA fine-tuning.
    """
    
    def __init__(self):
        self.encoder = get_encoder()

    async def process_dataset(self, input_path: Path, output_path: Path) -> None:
        """
        Process a JSONL dataset, adding semantic embeddings for each item.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        processed_data = []
        with open(input_path, "r") as f:
            for line in f:
                item = json.loads(line)
                # Combine question and answer for a richer semantic context
                text_to_encode = f"{item.get('question', '')} {item.get('answer', '')}"
                item["embedding"] = self.encoder.encode(text_to_encode).tolist()
                processed_data.append(item)
                
        with open(output_path, "w") as f:
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
        with open(input_path, "r") as f:
            for line in f:
                item = json.loads(line)
                question = item.get("question", "")
                answer = item.get("answer", "")
                
                # Format for instruction tuning
                finetune_item = {
                    "instruction": f"Solve the following reasoning problem: {question}",
                    "output": f"The final answer is \\boxed{{{answer}}}"
                }
                finetune_data.append(finetune_item)
                
        with open(output_path, "w") as f:
            for item in finetune_data:
                f.write(json.dumps(item) + "\n")
                
        logger.info(f"Prepared {len(finetune_data)} items for fine-tuning at {output_path}")
