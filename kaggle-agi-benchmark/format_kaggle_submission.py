import json
from pathlib import Path


# Paths
SOURCE_FILE = Path(__file__).parent / "evo_hiho_benchmark.jsonl"
SUBMISSION_FILE = Path(__file__).parent / "submission.jsonl"


def format_submission():
    if not SOURCE_FILE.exists():
        print(f"Source file {SOURCE_FILE.name} not found. Run generate script first.")
        return

    formatted_count = 0
    with open(SOURCE_FILE) as fin, open(SUBMISSION_FILE, "w") as fout:
        for line in fin:
            if not line.strip():
                continue

            task = json.loads(line)

            # Map our internal structure to the expected generic Kaggle Benchmark schema
            # We enforce standard 'question', 'options', 'answer', and 'cognitive_ability'
            submission_row = {
                "question": task.get("question", ""),
                "options": task.get("options", []),
                "answer": task.get("correct_answer", ""),
                "explanation": task.get("explanation", ""),
                "cognitive_ability": "Metacognition / Epistemic Humility",
                "domain": "Esoteric Physics & Mamba Continuous State Tracking",
            }

            fout.write(json.dumps(submission_row) + "\n")
            formatted_count += 1

    print(f"Successfully formatted {formatted_count} tasks to {SUBMISSION_FILE.name}.")
    print("Ready for Kaggle Hackathon Upload.")


if __name__ == "__main__":
    format_submission()
