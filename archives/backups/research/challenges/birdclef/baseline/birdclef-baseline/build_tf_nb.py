import json
from pathlib import Path


# Paths
BASE_DIR = Path(__file__).parent
TRAIN_PY = Path("scripts/train_birdclef_tf_baseline.py")


def get_file_content(path):
    with open(path) as f:
        return f.read()


train_content = get_file_content(TRAIN_PY)

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# BirdCLEF 2026: TensorFlow Baseline (EfficientNet-B0)\n",
                "This notebook trains a baseline model using TensorFlow to ensure environment compatibility.",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [train_content],
        },
    ],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.12"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

with open("birdclef-baseline/birdclef_baseline.ipynb", "w") as f:
    json.dump(notebook, f, indent=1)

print("BirdCLEF TF Notebook rebuilt.")
