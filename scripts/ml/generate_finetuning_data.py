"""Dataset generator for Gemma 4 QLoRA Fine-tuning.

Extracts core concepts from Cohezion Knowledge Graph and Physics modules
to create an Alpaca-style instruction dataset.
"""

import json
import os
import glob


def generate_dataset():
    data = []

    # 1. Extract from KEY_LEARNINGS.md
    learnings_path = "src/cohezion/knowledge_graph/KEY_LEARNINGS.md"
    if os.path.exists(learnings_path):
        with open(learnings_path, "r") as f:
            content = f.read()
            # Simple chunking by learning blocks (simulated)
            sections = content.split("### Learning")
            for section in sections[1:]:
                title = section.split("\n")[0].strip()
                data.append(
                    {
                        "instruction": f"Explain the concept of {title} within the Cohezion ecosystem.",
                        "input": "",
                        "output": section.strip(),
                    }
                )

    # 2. Extract from Physics modules
    physics_files = glob.glob("src/cohezion/physics/*.py")
    for pf in physics_files:
        module_name = os.path.basename(pf).replace(".py", "")
        with open(pf, "r") as f:
            content = f.read()
            # Extract module docstring
            if '"""' in content:
                docstring = content.split('"""')[1].strip()
                data.append(
                    {
                        "instruction": f"What is the purpose of the {module_name} physics module in Cohezion?",
                        "input": "",
                        "output": docstring,
                    }
                )

    # 3. Format for Training (Alpaca/Gemma Template)
    # text = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
    formatted_data = []
    for item in data:
        text = f"### Instruction:\n{item['instruction']}\n\n### Response:\n{item['output']}"
        formatted_data.append({"text": text})

    # 4. Save to JSONL
    output_path = "data/finetuning/gemma4/cohezion_physics_tek.jsonl"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        for item in formatted_data:
            f.write(json.dumps(item) + "\n")

    print(f"Generated {len(formatted_data)} training examples at {output_path}")


if __name__ == "__main__":
    generate_dataset()
