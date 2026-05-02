#!/usr/bin/env python3
"""Save hackathon data to vault via MCP server"""

import json

import requests


MCP_URL = "http://localhost:8360/mcp"

# Create hackathon entry
hackathon_data = {
    "type": "hackathon",
    "id": "oEOtLSSrPSVH60Ah",
    "challenge_id": "oEOtLSSrPSVH60Ah",
    "platform": "bluequbit",
    "score": 80,
    "problems_solved": 3,
    "problems_total": 10,
    "status": "in_progress",
    "solutions": [
        {
            "problem": "P1_little_peak",
            "qubits": 4,
            "answer": "1001",
            "points": 10,
            "status": "confirmed",
        },
        {
            "problem": "P2_swift_rise",
            "qubits": 28,
            "answer": "1100101101100011011000011100",
            "points": 20,
            "status": "confirmed",
        },
        {
            "problem": "P3_sharp_peak",
            "qubits": 44,
            "answer": "01011000100010110011111000001010101010110001",
            "points": 50,
            "status": "confirmed",
        },
        {
            "problem": "P7_heavy_hex_1275",
            "qubits": 45,
            "status": "retrying",
            "job_id": "tUfVijYQZZ8KkVxA",
            "notes": "bond_dim=16 insufficient, tried bond_dim=32, uniform distribution",
        },
        {
            "problem": "P8_grid_888_iswap",
            "qubits": 40,
            "status": "running",
            "job_id": "xg1wuFcwg3xJzceI",
        },
    ],
    "key_learnings": [
        "Bitstring reversal required: BlueQubit returns LSB, challenge expects MSB",
        "Bond dimension scaling: 44+ qubits need bond_dim > 32 for heavy hex",
        "Free tier limit: ~44-45 qubits reliably",
        "Heavy hex circuits need higher bond_dim than brick wall",
    ],
}

# Write to vault
response = requests.post(
    f"{MCP_URL}",
    json={
        "jsonrpc": "2.0",
        "method": "write_note",
        "params": {
            "path": "research/challenges/hackathon_oEOtLSSrPSVH60Ah/hackathon_data.json",
            "content": json.dumps(hackathon_data, indent=2),
            "tags": ["quantum", "bluequbit", "hackathon", "peaked_circuits"],
        },
        "id": 1,
    },
)

print(f"Vault write response: {response.status_code}")
print(response.json() if response.status_code == 200 else response.text)

# Also create a summary note
summary = """# BlueQubit Hackathon Status - April 2, 2026

## Challenge: oEOtLSSrPSVH60Ah

**Current Score: 80 points**

### Solved (Confirmed)
- P1_little_peak (4 qubits): `1001` - 10 points
- P2_swift_rise (28 qubits): `1100101101100011011000011100` - 20 points
- P3_sharp_peak (44 qubits): `01011000100010110011111000001010101010110001` - 50 points

### In Progress
- P4_golden_mountain (48 qubits): Retrying with bond_dim=8
- P7_heavy_hex_1275 (45 qubits): Retry completed, uniform distribution (no peak)
- P8_grid_888_iswap (40 qubits): **RUNNING** - Job xg1wuFcwg3xJzceI

### Needs Paid Tier
- P6_titan_pinnacle (62 qubits)
- P9_hqap_1917 (56 qubits)
- P10_heavy_hex_4020 (49 qubits)

### Key Learnings
1. Always reverse bitstrings: BlueQubit LSB → Challenge MSB
2. Heavy hex circuits need higher bond_dim than brick wall
3. Free tier reliable up to ~44-45 qubits
4. Uniform distribution = insufficient bond_dim

### Active Jobs (Check After Reboot)
- P8: Job xg1wuFcwg3xJzceI (40 qubits, mps.cpu, bond_dim=64)

### Funding Needed
~$0.50 for P4-P10 completion
"""

response2 = requests.post(
    f"{MCP_URL}",
    json={
        "jsonrpc": "2.0",
        "method": "write_note",
        "params": {
            "path": "research/challenges/hackathon_oEOtLSSrPSVH60Ah/status_summary.md",
            "content": summary,
            "tags": ["quantum", "bluequbit", "status", "active"],
        },
        "id": 2,
    },
)

print(f"\nSummary write response: {response2.status_code}")
