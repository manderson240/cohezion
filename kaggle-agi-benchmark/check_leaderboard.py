import json
import os
import subprocess
import time
from pathlib import Path

# Load .env file
def load_env():
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value
        print("Loaded environment variables from .env")

load_env()

COMPETITION_NAME = "kaggle-measuring-agi"
SUBMISSION_FILE = Path(__file__).parent / "submission.csv"

def submit_to_kaggle():
    if not SUBMISSION_FILE.exists():
        # Fallback to .jsonl if .csv not found
        fallback = SUBMISSION_FILE.with_suffix(".jsonl")
        if not fallback.exists():
            fallback = SUBMISSION_FILE.with_suffix(".json")
            
        if fallback.exists():
            print(f"Warning: {SUBMISSION_FILE} not found, using {fallback}")
            file_to_submit = fallback
        else:
            print(f"Error: Submission file not found.")
            return False
    else:
        file_to_submit = SUBMISSION_FILE
        
    print(f"Submitting {file_to_submit.name} to Kaggle competition '{COMPETITION_NAME}'...")
    
    cmd = [
        "kaggle", "competitions", "submit",
        "-c", COMPETITION_NAME,
        "-f", str(file_to_submit),
        "-m", "Automated submission via Cohezion Pipeline"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Submission successful:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("Failed to submit:")
        print(e.stderr)
        return False

def check_leaderboard():
    print(f"Polling leaderboard for '{COMPETITION_NAME}'...")
    cmd = [
        "kaggle", "competitions", "submissions",
        "-c", COMPETITION_NAME,
        "--csv"
    ]
    
    try:
        time.sleep(5) 
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("\n--- Recent Submissions ---")
        lines = result.stdout.strip().split("\n")
        for line in lines[:5]:
            print(line)
            
    except subprocess.CalledProcessError as e:
        print("Failed to fetch leaderboard:")
        print(e.stderr)

if __name__ == "__main__":
    success = submit_to_kaggle()
    if success:
        print("Waiting for evaluation...")
        time.sleep(15)
        check_leaderboard()
