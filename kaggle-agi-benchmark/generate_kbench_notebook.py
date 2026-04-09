import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
PY_SCRIPT = BASE_DIR / "evaluator_kbench.py"

def get_file_content(path):
    with open(path) as f:
        return f.read()

script_content = get_file_content(PY_SCRIPT)

# Split script content into headers and tasks to make it readable in cells if desired, 
# but for now we bundle it as one big execution block + %choose.

notebook = {
    "cells": [
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
                "5. Social Cognition (15 tasks): Theory of mind"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 1. Stable Dependency Resolution (Kaggle-Native)\n",
                "!pip install -q protobuf==5.26.1\n",
                "!pip install -q google-cloud-bigquery-storage==2.26.0\n",
                "!pip install -q git+https://github.com/Kaggle/kaggle-benchmarks.git"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [script_content]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "%choose agi_cognitive_framework_overall"
            ]
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
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

output_path = BASE_DIR / 'evaluator_kbench.ipynb'
with open(output_path, 'w') as f:
    json.dump(notebook, f, indent=2)
print(f'Notebook built at {output_path}')
