from pathlib import Path

import requests


def generate_arch():
    context = Path("REPO_SUMMARY.md").read_text()

    prompt = f"""
    ROLE: System Architect.
    TASK: Generate a Mermaid Class Diagram based on the repository structure.

    CONTEXT:
    {context}

    INSTRUCTION:
    1. Create a `classDiagram` that visualizes the high-level architecture.
    2. Focus on:
       - `src/cohezion/governance` (Nexus)
       - `src/cohezion/mycelium` (ShadowScripter)
       - `src/cohezion/expansion` (Loop)
       - `src/cohezion/system` (Ouroboros, Heartbeat, RepoMapper)
       - `src/cohezion/delegation` (PromptArchitect)
    3. Show relationships (arrows) where logical.
    4. Output ONLY the mermaid code.

    OUTPUT FORMAT:
    ```mermaid
    classDiagram
      ...
    ```
    """

    print("Generating Architecture Map...")
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "qwen2.5-coder:7b", "prompt": prompt, "stream": False},
        timeout=120,
    )

    if response.status_code == 200:
        content = response.json()["response"]
        # Extract mermaid block
        if "```mermaid" in content:
            content = content.split("```mermaid")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        output_path = Path("src/cohezion/knowledge_graph/ARCHITECTURE_MAP.mermaid")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content.strip())
        print(f"✅ Architecture Map saved to {output_path}")
    else:
        print(f"❌ Error: {response.status_code}")


if __name__ == "__main__":
    generate_arch()
