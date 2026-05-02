import json


py_file = "kaggle-agi-benchmark/evaluator_kbench.py"
ipynb_file = "kaggle-agi-benchmark/evaluator_kbench.ipynb"

with open(py_file) as f:
    py_content = f.read()

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Cohezion AGI Benchmark: 75 Tasks across 5 Cognitive Tracks\n",
            "\n",
            "Measuring progress toward AGI using kbench SDK.\n",
            "\n",
            "## Tracks\n",
            "1. Learning (15 tasks): Novel rule acquisition\n",
            "2. Metacognition (15 tasks): Epistemic humility\n",
            "3. Attention (15 tasks): Distractor resistance\n",
            "4. Executive Function (15 tasks): Dynamic constraint planning\n",
            "5. Social Cognition (15 tasks): Theory of mind",
        ],
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# 1. Upgrade protobuf and install kaggle-benchmarks (kbench) package\n",
            "!pip install -q --upgrade protobuf\n",
            "!pip install -q git+https://github.com/Kaggle/kaggle-benchmarks.git",
        ],
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": py_content.splitlines(keepends=True),
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": ["%choose agi_cognitive_framework_overall"],
    },
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"},
    },
    "nbformat": 4,
    "nbformat_minor": 4,
}

with open(ipynb_file, "w") as f:
    json.dump(notebook, f, indent=1)

print(f"Successfully generated {ipynb_file}")
