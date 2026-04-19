import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
MODEL_PY = BASE_DIR / "model.py"
TRAIN_PY = BASE_DIR / "train.py"


def get_file_content(path):
    with open(path) as f:
        return f.read()


model_content = get_file_content(MODEL_PY)
train_content = get_file_content(TRAIN_PY)

# Remove the import from cohezion since we bundle it
train_content = train_content.replace(
    "from cohezion.models.birdclef_baseline import BirdCLEFBaseline", ""
)

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# BirdCLEF 2026: PyTorch Baseline (EfficientNet-B0)\n",
                "This notebook trains a baseline model for bird species identification.",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ["!pip install -q torchvision"],
        },
        {"cell_type": "markdown", "metadata": {}, "source": ["## Model Definition"]},
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [model_content],
        },
        {"cell_type": "markdown", "metadata": {}, "source": ["## Training Loop"]},
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

with open(BASE_DIR / "birdclef_baseline.ipynb", "w") as f:
    json.dump(notebook, f, indent=1)

print(f"BirdCLEF Notebook rebuilt.")
