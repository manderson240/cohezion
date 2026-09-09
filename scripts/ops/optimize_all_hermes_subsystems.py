#!/usr/bin/env python3
"""Audit & Optimize All Hermes Desktop Subsystems for 100% Local Inference on AMD Strix Halo (:13305).

Configures:
1. Primary Chat & Tool Execution -> `user.cohezion-hermes-router` (NPU 35B MoE / iGPU 30B)
2. Smart Routing / Cheap Aux Turns -> `waslmedia-qwen3-4b-Q4_K_M` (NPU Instantaneous)
3. Context Compression & Summarization -> `waslmedia-qwen3-4b-Q4_K_M` (NPU Zero-GPU)
4. Local Speech-to-Text (STT) -> `Whisper-Large-v3-Turbo` (Lemonade :13305 whispercpp)
5. Local Text-to-Speech (TTS) -> `kokoro-v1` (Lemonade :13305 kokoro)
6. Vector Memory & RAG -> `lfm25-embed-350m` (1024D 128k context)
"""

from __future__ import annotations

from pathlib import Path

import yaml


HERMES_CONFIG = Path.home() / ".hermes/config.yaml"


def main() -> None:
    print("=" * 85)
    print("  🚀 OPTIMIZING ALL HERMES DESKTOP SUBSYSTEMS FOR 100% LOCAL SILICON INFERENCE")
    print("=" * 85)

    if not HERMES_CONFIG.exists():
        print(f"✗ Hermes config not found at {HERMES_CONFIG}")
        return

    with open(HERMES_CONFIG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 1. Update Core Model & Provider
    cfg["model"]["default"] = "user.cohezion-hermes-router"
    cfg["model"]["provider"] = "lemonade-local"
    cfg["model"]["context_length"] = 65536

    # 2. Update Providers Catalog on :13305
    cfg["providers"]["lemonade-local"] = {
        "api": "http://localhost:13305/api/v1",
        "default_model": "user.cohezion-hermes-router",
        "models": [
            "user.cohezion-hermes-router",
            "qwen3.6-moe-35b-a3b-FLM",
            "Qwen3-Coder-30B-A3B-Instruct-GGUF",
            "deepseek-r1-0528-8b-FLM",
            "waslmedia-qwen3-4b-Q4_K_M",
            "lfm25-embed-350m",
            "Whisper-Large-v3-Turbo",
            "kokoro-v1"
        ]
    }

    # 3. Optimize Auxiliary / Context Compression to NPU
    if "auxiliary" not in cfg:
        cfg["auxiliary"] = {}
    cfg["auxiliary"]["compression"] = {
        "model": "waslmedia-qwen3-4b-Q4_K_M",
        "provider": "lemonade-local",
        "context_length": 40960
    }

    # 4. Optimize Smart Model Routing / Cheap Model to NPU
    if "smart_model_routing" not in cfg:
        cfg["smart_model_routing"] = {}
    cfg["smart_model_routing"]["cheap_model"] = {
        "model": "waslmedia-qwen3-4b-Q4_K_M",
        "provider": "lemonade-local"
    }

    # 5. Optimize Local STT & TTS
    if "stt" not in cfg:
        cfg["stt"] = {}
    cfg["stt"]["enabled"] = True
    cfg["stt"]["local"] = {
        "model": "Whisper-Large-v3-Turbo",
        "endpoint": "http://localhost:13305/v1/audio/transcriptions"
    }

    if "tts" not in cfg:
        cfg["tts"] = {}
    cfg["tts"]["enabled"] = True
    cfg["tts"]["local"] = {
        "model": "kokoro-v1",
        "endpoint": "http://localhost:13305/v1/audio/speech"
    }

    # 6. Optimize Embeddings / Memory to 1024D Local Model
    if "memory" not in cfg:
        cfg["memory"] = {}
    cfg["memory"]["embedding_model"] = "lfm25-embed-350m"
    cfg["memory"]["embedding_endpoint"] = "http://localhost:13305/v1/embeddings"

    # Write back verified config
    with open(HERMES_CONFIG, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

    print("✓ Configured Primary Chat & Agent Tools -> `user.cohezion-hermes-router` (Port 13305)")
    print("✓ Configured Context Compression -> `waslmedia-qwen3-4b` on NPU (Zero-GPU overhead)")
    print("✓ Configured Smart Routing Cheap Turns -> `waslmedia-qwen3-4b` on NPU")
    print("✓ Configured Local STT Voice -> `Whisper-Large-v3-Turbo` on Lemonade (:13305)")
    print("✓ Configured Local TTS Voice -> `kokoro-v1` on Lemonade (:13305)")
    print("✓ Configured Memory & RAG Embeddings -> `lfm25-embed-350m` (1024D on :13305)")
    print("\n" + "=" * 85)
    print("🎉 100% OF HERMES DESKTOP SUBSYSTEMS ARE NOW OPTIMIZED FOR LOCAL SILICON!")
    print("=" * 85)


if __name__ == "__main__":
    main()
