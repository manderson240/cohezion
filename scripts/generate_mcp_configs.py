import json
from pathlib import Path


# Config source of truth (matching fleet.py)
SERVER_MAP = {
    "bmad": "cohezion.mcp.bmad_server",
    "coherence": "cohezion.mcp.coherence_server",
    "skills": "cohezion.mcp.skills_server_mcp",
    "research": "cohezion.mcp.research_server_mcp",
    "surreal": "cohezion.mcp.surreal_server_mcp",
    "swarm": "cohezion.mcp.swarm_server_mcp",
    "knowledge": "cohezion.mcp.knowledge_server_mcp",
}

DESCRIPTIONS = {
    "bmad": "108 BMAD commands for agile AI-driven development",
    "coherence": "HIHO coherence calculation and FLUME journey tracking",
    "skills": "Search, register, and invoke skills from the Cohezion registry",
    "research": "Discover SOTA research from arXiv and HuggingFace",
    "surreal": "Universe node tools and SurrealDB queries",
    "swarm": "Multi-agent debate and perspective synthesis",
    "knowledge": "RAG over library and skills knowledge base",
}

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
PYTHON_PATH = str(PROJECT_ROOT / ".venv" / "bin" / "python")
SRC_PATH = str(PROJECT_ROOT / "src")


def generate_gemini_settings():
    settings = {"mcpServers": {}}
    for name, module in SERVER_MAP.items():
        server_key = f"cohezion-{name}"
        settings["mcpServers"][server_key] = {
            "command": PYTHON_PATH,
            "args": ["-m", module],
            "env": {
                "PYTHONPATH": SRC_PATH,
                "MCP_TRANSPORT": "stdio",
                "BMAD_DATA_PATH": str(PROJECT_ROOT / "_bmad"),
            },
            "description": DESCRIPTIONS.get(name, ""),
        }

    output_path = PROJECT_ROOT / ".gemini" / "settings.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(settings, f, indent=2)
    print(f"Generated {output_path}")


def generate_external_mcp():
    mcp_servers = {"mcpServers": {}}
    for name, module in SERVER_MAP.items():
        server_key = f"cohezion-{name}"
        mcp_servers["mcpServers"][server_key] = {
            "command": PYTHON_PATH,
            "args": ["-m", module],
            "env": {
                "PYTHONPATH": SRC_PATH,
                "MCP_TRANSPORT": "stdio",
                "BMAD_DATA_PATH": str(PROJECT_ROOT / "_bmad"),
            },
        }

    output_path = PROJECT_ROOT / "mcp_servers.json"
    with open(output_path, "w") as f:
        json.dump(mcp_servers, f, indent=2)
    print(f"Generated {output_path}")


if __name__ == "__main__":
    generate_gemini_settings()
    generate_external_mcp()
