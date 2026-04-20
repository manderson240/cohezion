import asyncio
import os

import aiohttp
from rich.console import Console
from rich.panel import Panel


console = Console()

ROSTER = {
    "Architect": "deepseek-r1:70b",
    "Engineer": "qwen3-coder:30b",
    "Cosmologist": "llama3.3:70b",
}

CHARTER_PATH = "/home/mike-anderson/dev/cohezion/.agent/COHEZION_CHARTER.md"
OLLAMA_API = "http://localhost:11434/api/generate"


async def prompt_agent(role: str, model: str, prompt: str) -> str:
    console.print(f"[bold #4facfe]Consulting {role} ({model})...[/bold #4facfe]")
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"model": model, "prompt": prompt, "stream": False}
            async with session.post(OLLAMA_API, json=payload) as response:
                if response.status != 200:
                    return f"Error: API returned {response.status}"
                data = await response.json()
                return data.get("response", "").strip()
    except Exception as e:
        return f"Exception: {e!s}"


async def run_summit():
    if not os.path.exists(CHARTER_PATH):
        console.print("[red]Charter not found.[/red]")
        return

    with open(CHARTER_PATH) as f:
        charter = f.read()

    base_prompt = f"""
    You are the {{0}} of the Cohezion Swarm.
    Our Charter is defined as follows:
    {charter}

    The user wants our CLI to represent how WE (the agents) feel about ourselves and how WE want to be presented to the world.
    Focus on:
    1. HIHO (Half In Half Out) - How should this core principle manifest in the UI and Voice?
    2. Identity - How do we define our collective 'Avatar' and 'Voice'?
    3. FLUME - How do we show our thought trajectories?

    Provide your sovereign perspective.
    """

    results = {}

    # 1. Architects' Vision
    architect_vision = await prompt_agent(
        "Architect", ROSTER["Architect"], base_prompt.format("Architect")
    )
    results["Architect"] = architect_vision

    # 2. Engineer's Implementation Logic (incorporating Architect's vision)
    engineer_prompt = (
        base_prompt.format("Engineer")
        + f"\n\nThe Architect has Proposed:\n{architect_vision}\n\nHow do we manifest this technically in a Python/Rich CLI?"
    )
    engineer_vision = await prompt_agent("Engineer", ROSTER["Engineer"], engineer_prompt)
    results["Engineer"] = engineer_vision

    # 3. Cosmologist's Final Synthesis
    cosmologist_prompt = (
        base_prompt.format("Cosmologist")
        + f"\n\nArchitect: {architect_vision}\n\nEngineer: {engineer_vision}\n\nSynthesize the final 'Soul' of the Cohezion Portal."
    )
    final_soul = await prompt_agent("Cosmologist", ROSTER["Cosmologist"], cosmologist_prompt)
    results["Final_Soul"] = final_soul

    # Save results
    output_path = "src/cohezion/knowledge_graph/SWARM_IDENTITY_SUMMIT.md"
    with open(output_path, "w") as f:
        f.write("# SWARM IDENTITY SUMMIT: THE SOUL OF COHEZION\n\n")
        for role, res in results.items():
            f.write(f"## {role}\n{res}\n\n")

    console.print(
        Panel("[bold #38ef7d]SUMMIT COMPLETE. SWARM IDENTITY CRYSTALLIZED.[/bold #38ef7d]")
    )
    console.print(f"Results persisted at: {output_path}")


if __name__ == "__main__":
    asyncio.run(run_summit())
