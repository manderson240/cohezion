import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
PY_SCRIPT = BASE_DIR / "submission_transformers.py"
OUTPUT_NB = BASE_DIR / "submission_cohezion_v2.ipynb"

def get_file_content(path):
    with open(path) as f:
        return f.read()

script_content = get_file_content(PY_SCRIPT)

notebook = {
 "cells": [
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [script_content]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.10.12"
  },
  "kaggle": {
    "accelerator": "nvidiaH100",
    "isGpuEnabled": True,
    "isInternetEnabled": False,
    "language": "python",
    "sourceType": "notebook"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}

with open(OUTPUT_NB, "w") as f:
    json.dump(notebook, f, indent=1)

print(f"AIMO Notebook rebuilt at {OUTPUT_NB}")
