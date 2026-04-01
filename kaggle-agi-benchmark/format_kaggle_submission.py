import json
from pathlib import Path


# Paths
SOURCE_FILE = Path(__file__).parent / "evo_hiho_benchmark.json"
SUBMISSION_FILE = Path(__file__).parent / "submission.json"

def format_submission():
    """
    Formats the generated benchmark tasks into the final Kaggle submission JSON schema.
    
    The schema expects:
    {
      "train": [{"input": "...", "output": "..."}],
      "test": [{"input": "...", "output": "..."}]
    }
    """
    if not SOURCE_FILE.exists():
        print(f"Source file {SOURCE_FILE.name} not found. Run generate script first.")
        return

    with open(SOURCE_FILE, "r") as f:
        data = json.load(f)

    # In our generator, we already structure it as train/test
    # We ensure output fields are correctly mapped for the final submission
    submission_data = {
        "train": [],
        "test": []
    }

    for key in ["train", "test"]:
        for task in data.get(key, []):
            submission_data[key].append({
                "input": task.get("input", ""),
                "output": task.get("output", "")
            })

    with open(SUBMISSION_FILE, "w") as f:
        json.dump(submission_data, f, indent=2)

    total_tasks = len(submission_data["train"]) + len(submission_data["test"])
    print(f"Successfully formatted {total_tasks} tasks to {SUBMISSION_FILE.name}.")
    print("Ready for Kaggle submission.")

if __name__ == "__main__":
    format_submission()
