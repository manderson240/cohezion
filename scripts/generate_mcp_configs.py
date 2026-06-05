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
    "compound": "cohezion.mcp.compound_server",
    "rewards": "cohezion.mcp.servers.rewards.server",
    "security": "cohezion.mcp.servers.security.server",
    "journey": "cohezion.mcp.servers.journey.server",
    "github": "cohezion.mcp.servers.github.server",
    "huggingface": "cohezion.mcp.servers.huggingface.server",
    "traceability": "cohezion.mcp.servers.traceability.server",
}

DESCRIPTIONS = {
    "bmad": "108 BMAD commands for agile AI-driven development",
    "coherence": "HIHO coherence calculation and FLUME journey tracking",
    "skills": "Search, register, and invoke skills from the Cohezion registry",
    "research": "Discover SOTA research from arXiv and HuggingFace",
    "surreal": "Universe node tools and SurrealDB queries",
    "swarm": "Multi-agent debate and perspective synthesis",
    "knowledge": "RAG over library and skills knowledge base",
    "compound": "Unified interface for compound engineering",
    "rewards": "Agent XP and achievements system",
    "security": "Vulnerability scanning and analysis",
    "journey": "Agent journey and trajectory management",
    "github": "GitHub API integration",
    "huggingface": "Hugging Face Hub access",
    "traceability": "Traceability and V-Model health checking",
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


def update_mcp_config():
    config_path = PROJECT_ROOT / "mcp_config.json"
    if not config_path.exists():
        config = {"mcpServers": {}}
    else:
        with open(config_path) as f:
            config = json.load(f)
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    for name, module in SERVER_MAP.items():
        server_key = f"cohezion-{name}"
        config["mcpServers"][server_key] = {
            "command": PYTHON_PATH,
            "args": ["-m", module],
            "env": {
                "PYTHONPATH": SRC_PATH,
                "MCP_TRANSPORT": "stdio",
                "BMAD_DATA_PATH": str(PROJECT_ROOT / "_bmad"),
            },
        }

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Updated {config_path}")


if __name__ == "__main__":
    generate_gemini_settings()
    generate_external_mcp()
    update_mcp_config()
