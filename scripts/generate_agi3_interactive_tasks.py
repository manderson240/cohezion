import asyncio
import json
from pathlib import Path

from cohezion.compound.session_manager import CompoundSessionManager
from cohezion.swarm.compound_client import get_compound_client


# Output structure for the benchmark
BENCHMARK_FILE = Path("conductor/tracks/arc_agi_3_20260501/agi3_benchmark.json")

GENERATION_PROMPT = """
You are a master architect of ARC-AGI-3 interactive tasks.
Your goal is to create a novel AGENTIC logic puzzle that tests exploration and goal inference.

ARC-AGI-3 Key Differences:
1. Turn-based: Tasks are solved over multiple actions.
2. Exploration: The agent must discover hidden invariants via interaction.
3. Goal Inference: The final objective is not explicitly stated.

Task Structure:
- training_sequences: A list of 2-3 sequences. Each sequence shows a series of (state, action, reward, next_state) tuples.
- test_environment: An initial grid state for the agent to interact with.
- goal_invariant: The hidden rule that defines completion.

Example Goal Invariants:
- "Touch all blue pixels to turn them red."
- "Move the green block to the same row as the red pixel."
- "Repeat the input pattern in the bottom-right corner using the 'copy' action."

Rules:
1. Every grid must be a 2D array of integers (0-9).
2. Actions are discrete integers (0-9): 0=None, 1=Up, 2=Down, 3=Left, 4=Right, 5=Click, 6=Color1...
3. Output ONLY valid JSON.

Example Output Format:
{
  "name": "Hidden Object Alignment",
  "training_sequences": [
    {
      "steps": [
        {"state": [[0,0,0],[0,2,0],[3,0,0]], "action": 4, "reward": 0.1, "next_state": [[0,0,0],[0,0,2],[3,0,0]]},
        {"state": [[0,0,0],[0,0,2],[3,0,0]], "action": 2, "reward": 1.0, "next_state": [[0,0,0],[0,0,0],[3,0,2]]}
      ],
      "goal_reached": true
    }
  ],
  "test_environment": {
    "initial_state": [[0,0,3],[0,0,0],[1,0,0]]
  },
  "goal_invariant": "Move color 1 to same row as color 3."
}

Create a new, unique interactive task now.
"""


async def generate_batch(num_tasks: int = 3):
    # Ensure directory exists
    BENCHMARK_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load existing tasks if any
    if BENCHMARK_FILE.exists():
        with open(BENCHMARK_FILE) as f:
            try:
                tasks = json.load(f)
            except json.JSONDecodeError:
                tasks = []
    else:
        tasks = []

    async with CompoundSessionManager() as mgr:
        mgr.start_session(max_cache_entries=256)

        for i in range(num_tasks):
            print(f"Generating AGI-3 task {i + 1}/{num_tasks}...")

            unique_prompt = (
                GENERATION_PROMPT
                + f"\n\nTask ID: AGI3_Interactive_{len(tasks)} - Generate a unique agentic puzzle."
            )

            async def real_execute(*args, i=i, unique_prompt=unique_prompt, **kwargs):
                client = get_compound_client()
                # Use qwen3.5:cloud or gemini-3-flash-preview:cloud from the list
                response = await client.generate(
                    prompt=unique_prompt,
                    model="qwen3.5:cloud",
                    temperature=0.8,
                    system="You are an ARC-AGI-3 architect. Output ONLY valid JSON.",
                )

                if isinstance(response, tuple):
                    response_text = response[0]
                elif hasattr(response, "response"):
                    response_text = response.response
                else:
                    response_text = str(response)

                try:
                    text = response_text.strip()
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start != -1 and end != -1:
                        data = json.loads(text[start:end])
                        if "training_sequences" in data and "test_environment" in data:
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
                task_data = result.get("output", result) if isinstance(result, dict) else result

                if isinstance(task_data, dict) and "training_sequences" in task_data:
                    tasks.append(task_data)
                    print(f"SUCCESS: Generated AGI-3 task {i + 1}")

                    with open(BENCHMARK_FILE, "w") as f:
                        json.dump(tasks, f, indent=2)
                else:
                    print(f"FAILED validation: {task_data}")

        mgr.end_session()

    print(f"Successfully generated/updated {len(tasks)} AGI-3 tasks.")


if __name__ == "__main__":
    asyncio.run(generate_batch())
