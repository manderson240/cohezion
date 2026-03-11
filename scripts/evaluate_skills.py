import asyncio
import json
import logging
from pathlib import Path

import httpx


logging.basicConfig(level=logging.INFO)


async def evaluate_skill(model: str, skill_path: str, prompt: str):
    skill_content = Path(skill_path).read_text()
    system_prompt = f"You are an AI executing the following skill strictly. Follow the format and constraints requested:\n\n{skill_content}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "system": system_prompt,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
                timeout=120.0,
            )
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Exception: {e}"


async def main():
    models_to_test = ["gemma3:4b", "qwen2.5-coder:7b", "phi4:latest"]
    target_skill = "src/cohezion/skills/FLUME_METHODOLOGY_PRIME.md"
    task_prompt = "Apply the FLUME methodology to compress the concept of a 'binary search tree' into a latent semantic vector description. Provide the resulting encoded representation as described in the INSTRUCTION SET."

    print("--- Cross-Model Skill Evaluation ---")
    print(f"Target Skill: {target_skill}")
    print(f"Task: {task_prompt}\n")

    results = {}
    for model in models_to_test:
        print(f"Evaluating model: {model} ... ", end="")
        output = await evaluate_skill(model, target_skill, task_prompt)

        success_score = 0
        if "vector" in output.lower() or "encoder" in output.lower() or "latent" in output.lower():
            success_score += 0.5
        if (
            "binary search tree" in output.lower()
            or "bst" in output.lower()
            or "node" in output.lower()
        ):
            success_score += 0.5

        print(f"Score: {success_score}")
        results[model] = {
            "score": success_score,
            "output_preview": output[:200].replace("\n", " ") + "...",
        }

    print("\nEvaluation Summary:")
    print(json.dumps(results, indent=2))

    Path("src/cohezion/knowledge_graph/reports").mkdir(parents=True, exist_ok=True)
    with open("src/cohezion/knowledge_graph/reports/CROSS_MODEL_EVALUATION.md", "w") as f:
        f.write("# Cross-Model Skill Evaluation\n\n")
        f.write(f"**Target Skill:** `{target_skill}`\n")
        f.write(f"**Task Prompt:** `{task_prompt}`\n\n")
        for m, data in results.items():
            f.write(f"## Model: {m}\n")
            f.write(f"**Score**: {data['score']}/1.0\n\n")
            f.write(f"**Preview**:\n```text\n{data['output_preview']}\n```\n\n")
    print("Report written to src/cohezion/knowledge_graph/reports/CROSS_MODEL_EVALUATION.md")


if __name__ == "__main__":
    asyncio.run(main())
