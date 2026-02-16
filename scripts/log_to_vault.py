#!/usr/bin/env python3
"""
Log portfolio creation to vault
"""
import httpx
import json

session = httpx.Client()

# Initialize MCP session
init_response = session.post(
    'http://localhost:8360/mcp',
    json={
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'initialize',
        'params': {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'portfolio-logger', 'version': '1.0'}
        }
    },
    headers={
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
)

print(f"Init: {init_response.status_code}")

# Log experiment
experiment_data = {
    "project": "cohezion",
    "hypothesis": "Complete Anthropic portfolio with FLUME analysis, journey tracking, and research paper",
    "method": "Created portfolio structure, ran FLUME analysis, enhanced research paper, documented metrics",
    "result": "Successfully generated comprehensive portfolio in docs/portfolio/",
    "learnings": [
        "FLUME achieves 8:1 compression with 87.5% dimensionality reduction",
        "12D journey tracking enables quantified coherence measurement",
        "R-Zero protocol demonstrates anti-fragile behavior across 24,000 simulations",
        "Portfolio structure: README + paper + metrics + flume + journeys"
    ]
}

exp_response = session.post(
    'http://localhost:8360/mcp',
    json={
        'jsonrpc': '2.0',
        'id': 2,
        'method': 'tools/call',
        'params': {
            'name': 'vault_log_experiment',
            'arguments': experiment_data
        }
    },
    headers={
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
)

print(f"Log experiment: {exp_response.status_code}")
print(exp_response.text[:500])

# Extract pattern
pattern_data = {
    "source_path": "docs/portfolio/",
    "pattern_name": "Anthropic Portfolio Structure",
    "description": "Complete portfolio for Research Engineer, Universes role with FLUME, journeys, and research paper",
    "code_example": """
# Portfolio structure:
docs/portfolio/
├── README.md              # Executive summary
├── RESEARCH_PAPER.md      # Full methodology  
├── METRICS.json           # Quantified results
├── flume/                 # VAE analysis
└── journeys/              # 12D tracking
""",
    "domain": "portfolio, research, anthropic"
}

pat_response = session.post(
    'http://localhost:8360/mcp',
    'json': {
        'jsonrpc': '2.0',
        'id': 3,
        'method': 'tools/call',
        'params': {
            'name': 'vault_extract_pattern',
            'arguments': pattern_data
        }
    },
    headers={
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
)

print(f"Extract pattern: {pat_response.status_code}")
print("Vault logging complete!")
