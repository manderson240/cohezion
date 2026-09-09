#!/usr/bin/env python3
"""Generate Native Obsidian .canvas Mindmap for Cohezion Cognitive Swarm.

Creates an interactive, zoomable 2D canvas in ~/vaults/cohezion-vault/architecture.canvas
visualizing the full platform topology: Hardware -> Models -> Security -> Engines -> Memory.
"""

import json
import os

VAULT_CANVAS_PATH = "/home/mike-anderson/vaults/cohezion-vault/architecture.canvas"

canvas_data = {
    "nodes": [
        {
            "id": "node_hardware",
            "x": -600,
            "y": -200,
            "width": 380,
            "height": 260,
            "type": "text",
            "text": "## 💻 Hardware Substrate\n**AMD Strix Halo**\n- **128GB LPDDR5X UMA** @ 273 GB/s\n- **Radeon 8060S iGPU** (16 TFLOPS)\n- **XDNA2 NPU** (Dedicated Matrix Compute)\n- **Ryzen 9 7945HX CPU** (16C/32T)"
        },
        {
            "id": "node_models",
            "x": -100,
            "y": -200,
            "width": 380,
            "height": 260,
            "type": "text",
            "text": "## 🧠 Model Routing Hierarchy\n**Lemonade OmniRouter (:13305)**\n- **iGPU**: `gpt-oss-20b-mxfp4` (128K KV, 60 tok/s)\n- **NPU**: `qwen3.6-moe-35b` (3B active)\n- **Edge NPU**: `llama3.2-1b` (< 100ms routing)\n- **Ollama Cloud**: `deepseek-v4-pro`, `qwen-397b`"
        },
        {
            "id": "node_security",
            "x": 400,
            "y": -200,
            "width": 380,
            "height": 260,
            "type": "text",
            "text": "## 🛡️ Kernel & AST Isolation\n**Multi-Layer Security**\n- **AutoHarness AST Gate** (< 0.2ms zero-cost)\n- **Bubblewrap Namespaces** (CLONE_NEWNS/PID/NET)\n- **cgroup v2 Hardware Bounds** (systemd-run MemoryMax=4G)\n- **OOM Headroom Governor** (>= 20.0 GiB safe floor)"
        },
        {
            "id": "node_engines",
            "x": -350,
            "y": 180,
            "width": 420,
            "height": 280,
            "type": "text",
            "text": "## 🌌 World Models & Manifold Physics\n**FLUME & Physical Engines**\n- **2048D Poincaré Ball Manifold** (Hyperbolic distance)\n- **HIHO 0.5 Reality Precipitation** (432 Hz loss gradients)\n- **Bioelectric Swarm** (Gap-junction 9x light-cone expansion)\n- **EVO Simulation Engine** (Matsumoto & Shoulders)"
        },
        {
            "id": "node_memory",
            "x": 200,
            "y": 180,
            "width": 420,
            "height": 280,
            "type": "text",
            "text": "## 🔮 Dual-Engine Cognitive Memory\n**SurrealDB v3 + Obsidian Vault**\n- **SurrealDB 3.2.3**: 2048D HNSW vector index, BM25 text search, `RELATE` graph lineage\n- **Obsidian Vault**: 13K+ Kanban cards, 248+ Key Learnings, bidirectional `[[wikilinks]]`\n- **EventBus Bridge**: Bi-temporal event streaming"
        }
    ],
    "edges": [
        {"id": "edge_hw_to_models", "fromNode": "node_hardware", "fromSide": "right", "toNode": "node_models", "toSide": "left"},
        {"id": "edge_models_to_sec", "fromNode": "node_models", "fromSide": "right", "toNode": "node_security", "toSide": "left"},
        {"id": "edge_models_to_eng", "fromNode": "node_models", "fromSide": "bottom", "toNode": "node_engines", "toSide": "top"},
        {"id": "edge_sec_to_mem", "fromNode": "node_security", "fromSide": "bottom", "toNode": "node_memory", "toSide": "top"},
        {"id": "edge_eng_to_mem", "fromNode": "node_engines", "fromSide": "right", "toNode": "node_memory", "toSide": "left"}
    ]
}

with open(VAULT_CANVAS_PATH, "w", encoding="utf-8") as f:
    json.dump(canvas_data, f, indent=2)

print(f"✅ Generated Native Obsidian Canvas: {VAULT_CANVAS_PATH}")
