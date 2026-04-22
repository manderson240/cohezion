#!/bin/bash
export PYTHONPATH=src
export CLOUD_VAULT_API_KEY="a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263"
export MCP_PORT=8379
export MCP_TRANSPORT=http
echo "Starting compound server..."
.venv/bin/python3 -m cohezion.mcp.compound_server >> logs/mcp_compound_dogfood.log 2>&1
