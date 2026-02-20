import json
from pathlib import Path


# MCP Config for SurrealDB
mcp_config = {
    "mcpServers": {
        "surrealmcp": {
            "command": "npx",
            "args": ["-y", "@surrealdb/mcp-server"],
            "env": {
                "SURREALDB_URL": "ws://localhost:8000/rpc",
                "SURREALDB_NS": "cohezion",
                "SURREALDB_DB": "core",
            },
        },
        "cohezion-skills": {
            "command": "./.venv/bin/python3",
            "args": ["cohezion_skill_mcp.py"],
        },
    }
}

config_path = Path("config/mcp_config.json")
config_path.parent.mkdir(exist_ok=True)
config_path.write_text(json.dumps(mcp_config, indent=2))

print(f"✅ MCP Configuration written to {config_path}")
print("To use these servers, point your MCP client to this configuration file.")
