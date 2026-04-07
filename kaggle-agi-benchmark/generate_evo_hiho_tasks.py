import argparse
import asyncio
import json
import re
from pathlib import Path

from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.swarm.compound_client import get_compound_client


# Output structure for the benchmark
BENCHMARK_FILE = Path(__file__).parent / "evo_hiho_benchmark.json"

GENERATION_PROMPT = """
You are a master architect of ARC-AGI tasks. Your goal is to create a novel logic puzzle that tests abstract reasoning.
The puzzle consists of 2 training examples and 1 test input.

Logic Examples:
- Color spreading: A single pixel of color X spreads to fill its 3x3 neighborhood.
- Object reflection: An object is reflected across a horizontal axis.
- Pattern repetition: A 2x2 pattern is repeated to fill a 6x6 grid.

Rules:
1. Every grid must be a 2D array of integers (0-9).
2. The logic must be 100% consistent across all examples.
3. Be creative and challenging.
4. Output ONLY valid JSON. No markdown code blocks.

Example Output Format:
{
  "train": [
    {
      "input": [[0, 0, 0], [0, 5, 0], [0, 0, 0]],
      "output": [[5, 5, 5], [5, 5, 5], [5, 5, 5]]
    },
    {
      "input": [[0, 0, 0, 0], [0, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
      "output": [[2, 2, 2, 0], [2, 2, 2, 0], [2, 2, 2, 0], [0, 0, 0, 0]]
    }
  ],
  "test": [
    {
      "input": [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 3, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]],
      "output": [[0, 0, 0, 0, 0], [0, 3, 3, 3, 0], [0, 3, 3, 3, 0], [0, 3, 3, 3, 0], [0, 0, 0, 0, 0]]
    }
  ]
}

Create a new, unique task now.
"""


async def generate_batch(num_tasks: int = 5):
    # Load existing tasks if any
    if BENCHMARK_FILE.exists():
        with open(BENCHMARK_FILE, "r") as f:
            try:
                tasks = json.load(f)
            except:
                tasks = []
    else:
        tasks = []

    async with CompoundSessionManager() as mgr:
        mgr.start_session(max_cache_entries=256)

        for i in range(num_tasks):
            print(f"Generating task {i + 1}/{num_tasks}...")
            
            # Make the prompt unique to prevent caching
            unique_prompt = GENERATION_PROMPT + f"\n\nTask ID: {i} - Generate a unique task."
            
            async def real_execute(*args, i=i, unique_prompt=unique_prompt, **kwargs):
                client = get_compound_client()
                # Use qwen3-coder:30b for high-quality logic and JSON
                response = await client.generate(
                    prompt=unique_prompt,
                    model="qwen3-coder:30b", 
                    temperature=0.7,
                    system="You are a master of ARC-AGI. Output ONLY valid JSON. No markdown."
                )
                
                if isinstance(response, tuple):
                    response_text = response[0]
                elif hasattr(response, "response"):
                    response_text = response.response
                else:
                    response_text = str(response)

                try:
                    # Clean and parse JSON
                    text = response_text.strip()
                    # Find first { and last }
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start != -1 and end != -1:
                        data = json.loads(text[start:end])
                        if "train" in data and "test" in data:
                            return data
                    return None
                except Exception as e:
                    print(f"Parse error: {e}")
                    return None

            success, result = await mgr.execute_aligned(
                request=unique_prompt,
                execute_fn=real_execute,
                skill_name="auto",
            )

            if success and result:
                # Unwrap the result if it was wrapped by execute_aligned
                task_data = result.get("output", result) if isinstance(result, dict) else result
                
                # Basic validation
                if isinstance(task_data, dict) and "train" in task_data and "test" in task_data:
                    tasks.append(task_data)
                    print(f"SUCCESS: Generated task {i+1}")
                    print(json.dumps(task_data, indent=2))
                    
                    # Save after each task
                    with open(BENCHMARK_FILE, "w") as f:
                        json.dump(tasks, f, indent=2)
                else:
                    print(f"FAILED validation: {task_data}")

        mgr.end_session()

    if tasks:
        print(f"Successfully generated/updated {len(tasks)} tasks.")
    else:
        print("No tasks generated successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_tasks", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(generate_batch(num_tasks=args.num_tasks))
