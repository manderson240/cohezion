import asyncio
import json
import logging
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from cohezion.core.mcp_client import create_mcp_client

async def test_capture():
    logging.basicConfig(level=logging.INFO)
    
    # Connect to the background compound server (running on 8379)
    client = create_mcp_client(server_url="http://localhost:8379", api_key="cohezion-dev-key")
    
    # Mock result for dogfooding
    result = {
        "request": "Optimize start-mcp-servers.sh with robust process management",
        "tokens_used": 1200,
        "cache_hits": 2,
        "duration_seconds": 120,
        "coherence": 0.98,
        "success": True,
        "skill_used": "MCP_SPECIALIST_PRIME",
        "lessons": [
            "Background server processes need log redirection to avoid terminal hang",
            "PID tracking is essential for reliable pkill cleanup",
            "Stateless FastMCP servers require explicit HTTP transport flag for multi-client access"
        ]
    }
    
    print(f"Calling learning_process_execution on {client.config.server_url}...")
    try:
        client.connect()
        # Pass server_url to tool to point to vault
        response = client._call_tool(
            "learning_process_execution",
            {
                "execution_result_json": json.dumps(result),
                "server_url": "http://localhost:8360"
            }
        )
        print("Response:", response)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_capture())
