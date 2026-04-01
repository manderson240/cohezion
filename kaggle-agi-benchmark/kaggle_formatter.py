import json
import logging
from pathlib import Path


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BENCHMARK_FILE = Path(__file__).resolve().parent / "submission.jsonl"
OUTPUT_FILE = Path(__file__).resolve().parent / "kaggle_benchmark.json"

def format_kaggle_benchmark() -> None:
    """Read submission.jsonl and format it as a valid Kaggle JSON."""
    if not BENCHMARK_FILE.exists():
        logger.error(f"Benchmark file not found at {BENCHMARK_FILE}")
        return

    train_data = []
    test_data = []

    with open(BENCHMARK_FILE, "r") as f:
        lines = f.readlines()

    # Split 80/20 train/test
    split_idx = int(len(lines) * 0.8)

    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            task = json.loads(line)
            
            # Construct Kaggle input
            input_text = (
                f"Question:\n{task.get('question')}\n\n"
                f"Options:\n{json.dumps(task.get('options', []))}\n"
            )
            output_text = task.get('correct_answer')
            
            formatted_task = {
                "input": input_text,
                "output": output_text
            }
            
            if i < split_idx:
                train_data.append(formatted_task)
            else:
                test_data.append(formatted_task)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Skipping invalid JSON line {i}: {e}")

    kaggle_schema = {
        "train": train_data,
        "test": test_data
    }

    with open(OUTPUT_FILE, "w") as out:
        json.dump(kaggle_schema, out, indent=2)

    logger.info(f"Formatted and saved Kaggle benchmark to {OUTPUT_FILE}")
    logger.info(f"Train samples: {len(train_data)}, Test samples: {len(test_data)}")

if __name__ == "__main__":
    format_kaggle_benchmark()
