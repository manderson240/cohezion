from pathlib import Path

import requests


# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
CRITIC_MODEL = "deepseek-r1:70b"  # Verified available
ARCHITECT_MODEL = "qwen3-coder:30b"  # Verified available
TARGET_FILE = "src/cohezion/simulation/fractal_universe.py"


def call_ollama(model, prompt):
    print(f"Thinking with {model}...")
    try:
        response = requests.post(
            OLLAMA_URL, json={"model": model, "prompt": prompt, "stream": False}
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        print(f"Error calling {model}: {e}")
        return None


def run_debate():
    # Read the code
    code = Path(TARGET_FILE).read_text()

    # 1. Critic Round
    critic_prompt = f"""
    Internal Monologue: Criticize the following simulation code:
    {code}

    Identify 3 major weaknesses in:
    1. Physics realism (entropy handling)
    2. Agent autonomy (simple greedy logic)
    3. Manifold interactions (hardcoded/random)

    Be harsh. We need next-level complexity for a 'Fractal Universe'.
    """

    critique = call_ollama(CRITIC_MODEL, critic_prompt)
    if not critique:
        return

    print("\n=== CRITIQUE ===\n")
    print(critique)

    # 2. Architect Round
    architect_prompt = f"""
    The Critic has analyzed our code:
    {code}

    Critique:
    {critique}

    Internal Monologue: Propose concrete Python code changes to address these flaws.
    Focus on:
    - Adding 'Memory' to Agents.
    - Making Manifold sectors interact (diffusion).
    - Adding a 'Global Field' equation.

    Output the suggested class updates in Python.
    """

    proposal = call_ollama(ARCHITECT_MODEL, architect_prompt)
    if not proposal:
        return

    print("\n=== PROPOSAL ===\n")
    print(proposal)

    # Save to file
    with open("EVOLUTION_PROPOSAL.md", "w") as f:
        f.write("# Evolution Proposal\n\n")
        f.write("## Critique\n")
        f.write(critique + "\n\n")
        f.write("## Proposal\n")
        f.write(proposal + "\n")


if __name__ == "__main__":
    run_debate()
