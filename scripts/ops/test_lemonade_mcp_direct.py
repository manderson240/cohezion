#!/usr/bin/env python3
"""Direct In-Process FastMCP Client for Lemonade Server MCP.

Invokes the FastMCP server `cohezion.mcp.lemonade_server_mcp` directly without external HTTP overhead.
"""

import asyncio
from cohezion.mcp.lemonade_server_mcp import (
    lemonade_list_models,
    lemonade_chat,
    lemonade_server_status
)

async def main():
    print("=" * 80)
    print("🍋 DIRECT FAST-MCP IN-PROCESS LEMONADE TOOLS AUDIT")
    print("=" * 80)

    # 1. Query server status via FastMCP tool
    print("▶ 1. Calling FastMCP `lemonade_server_status()`...")
    status = await lemonade_server_status()
    print(f"  • Server Status: {status.get('status')} | Version: {status.get('version')} | Port: {status.get('port')}")

    # 2. Query models via FastMCP tool
    print("\n▶ 2. Calling FastMCP `lemonade_list_models(downloaded_only=True)`...")
    models = await lemonade_list_models(downloaded_only=True)
    print(f"  • Discovered {models.get('count')} downloaded models on Port 13305")

    # 3. Chat completion via FastMCP tool
    print("\n▶ 3. Calling FastMCP `lemonade_chat()` with resident Gemma-4-E4B-it-GGUF...")
    chat_res = await lemonade_chat(
        messages=[{"role": "user", "content": "In 15 words, confirm you are executing locally through Lemonade FastMCP."}],
        model="Gemma-4-E4B-it-GGUF",
        max_tokens=50,
        temperature=0.1
    )
    print(f"  • Model: {chat_res.get('model')}")
    print(f"  • Response:\n    \"{chat_res.get('content', '').strip()}\"")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
