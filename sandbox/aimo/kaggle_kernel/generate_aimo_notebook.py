import json
import argparse
from pathlib import Path

def generate_notebook(script_path, output_path):
    script_path = Path(script_path)
    output_path = Path(output_path)
    
    with open(script_path) as f:
        script_content = f.read()

    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [script_content],
            }
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.12"},
            "kaggle": {
                "accelerator": "nvidiaH100",
                "isGpuEnabled": True,
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    with open(output_path, "w") as f:
        json.dump(notebook, f, indent=1)

    print(f"AIMO Notebook created at {output_path} from {script_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Kaggle AIMO notebook from python script.")
    parser.add_argument("--script", default="submission_v42_harness.py", help="Input python script")
    parser.add_argument("--output", default="submission_cohezion_v2.ipynb", help="Output notebook path")
    args = parser.parse_args()
    
    generate_notebook(args.script, args.output)
