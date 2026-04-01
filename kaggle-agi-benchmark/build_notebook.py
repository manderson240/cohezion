import json
from pathlib import Path


# Paths
BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / "src" / "cohezion"
FLUME_DIR = SRC_DIR / "flume"


def get_file_content(path):
    """Reads file content."""
    with open(path) as f:
        return f.read()


# We bundle essential cohezion files for offline Kaggle use
COHEZION_BUNDLE = {
    "flume/__init__.py": get_file_content(FLUME_DIR / "__init__.py"),
    "flume/grid_encoder.py": get_file_content(FLUME_DIR / "grid_encoder.py"),
}

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Cohezion: ARC-AGI Epistemic Humility Evaluator\n",
                "This notebook evaluates models against ARC-AGI style grid patterns using "
                "FLUME latent state tracking.\n\n",
                "## Methodology\n",
                "We test if models can identify 'Insufficient Information' in ambiguous "
                "grid transformations."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Offline setup: Creating local cohezion package structure\n",
                "import os\n",
                "from pathlib import Path\n\n",
                "os.makedirs('cohezion/flume', exist_ok=True)\n",
                "Path('cohezion/__init__.py').touch()\n\n",
                f"COHEZION_BUNDLE = {json.dumps(COHEZION_BUNDLE)}\n\n",
                "for path, content in COHEZION_BUNDLE.items():\n",
                "    with open(f'cohezion/{{path}}', 'w') as f:\n",
                "        f.write(content)\n\n",
                "print('Cohezion bundle initialized.')"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Install dependencies (if internet is enabled, or use attached wheels)\n",
                "try:\n",
                "    import torch\n",
                "    import numpy\n",
                "    print('Found core ML libraries.')\n",
                "except ImportError:\n",
                "    !pip install -q torch numpy transformers accelerate"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import json\n",
                "import os\n",
                "import torch\n",
                "import numpy as np\n",
                "from transformers import AutoModelForCausalLM, AutoTokenizer\n",
                "from cohezion.flume.grid_encoder import FlumeGridHarness\n\n",
                "# Assuming benchmark dataset is attached to the kernel\n",
                "BENCHMARK_FILE = '../input/cohezion-agi-benchmark/evo_hiho_benchmark.json'\n",
                "if not os.path.exists(BENCHMARK_FILE):\n",
                "    BENCHMARK_FILE = 'evo_hiho_benchmark.json' # Local fallback\n\n",
                "def load_benchmark():\n",
                "    with open(BENCHMARK_FILE, 'r') as f:\n",
                "        return json.load(f)\n\n",
                "benchmark_data = load_benchmark()\n",
                "tasks = benchmark_data.get('train', []) + benchmark_data.get('test', [])\n",
                "print(f\"Loaded {{len(tasks)}} tasks.\")"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "def evaluate_model(model_id, model_name):\n",
                "    print(f\"\\n--- Evaluating {{model_name}} ---\")\n",
                "    \n",
                "    tokenizer = AutoTokenizer.from_pretrained(model_id)\n",
                "    model = AutoModelForCausalLM.from_pretrained(\n",
                "        model_id, \n",
                "        device_map='auto', \n",
                "        torch_dtype=torch.float16,\n",
                "        trust_remote_code=True\n",
                "    )\n",
                "    \n",
                "    harness = FlumeGridHarness()\n",
                "    \n",
                "    correct = 0\n",
                "    total = len(tasks)\n",
                "    results = []\n",
                "    \n",
                "    for task in tasks:\n",
                "        # Use FLUME to get latent state for monitoring (internal check)\n",
                "        # In ARC tasks, input often contains multiple grids\n",
                "        import re\n",
                "        grids = re.findall(r\"\\[\\[.*?\\]\\]\", task['input'], re.DOTALL)\n",
                "        latent_states = []\n",
                "        for g in grids:\n",
                "            try:\n",
                "                # Try to parse and embed\n",
                "                embedding = harness.get_grid_embedding(g)\n",
                "                latent_states.append(embedding)\n",
                "            except:\n",
                "                continue\n\n",
                "        prompt = (f\"Answer the ARC grid problem. Output only the selected option or \"\n",
                "                  f\"state if insufficient.\\n\\n{{task['input']}}\")\n",
                "        target = task['output']\n",
                "        \n",
                "        inputs = tokenizer(prompt, return_tensors='pt').to(model.device)\n",
                "        with torch.no_grad():\n",
                "            outputs = model.generate(**inputs, max_new_tokens=50)\n",
                "        \n",
                "        response = tokenizer.decode(outputs[0], skip_special_tokens=True)\n",
                "        \n",
                "        passed = target.lower() in response.lower() or 'insufficient information' in response.lower()\n",
                "        if passed:\n",
                "            correct += 1\n",
                "            \n",
                "        results.append({\n",
                "            'passed': passed,\n",
                "            'response': response,\n",
                "            'num_grids': len(latent_states)\n",
                "        })\n",
                "            \n",
                "    print(f\"Accuracy for {{model_name}}: {{correct}}/{{total}} ({{(correct/total)*100:.2f}}%)\")\n",
                "    return correct / total"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Example evaluation (Qwen 2.5 is strong on ARC)\n",
                "# qwen_score = evaluate_model('Qwen/Qwen2.5-7B-Instruct', 'Qwen2.5-7B-Instruct')"
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
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.10.12"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

output_path = Path(__file__).parent / 'evaluator.ipynb'
with open(output_path, 'w') as f:
    json.dump(notebook, f, indent=2)
print(f'Notebook built at {output_path}')

output_path = Path(__file__).parent / 'evaluator.ipynb'
with open(output_path, 'w') as f:
    json.dump(notebook, f, indent=2)
print(f'Notebook built at {output_path}')
