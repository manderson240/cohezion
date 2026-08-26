"""Biohub 3D Cell Tracking Baseline Kernel."""
import os
import shutil
import pandas as pd

def main():
    sample_sub = "/kaggle/input/biohub-cell-tracking-during-development/sample_submission.csv"
    if os.path.exists(sample_sub):
        df = pd.read_csv(sample_sub)
        df.to_csv("submission.csv", index=False)
        print("Successfully copied sample submission to submission.csv")
    else:
        print("Warning: sample_submission.csv not found")

if __name__ == "__main__":
    main()
