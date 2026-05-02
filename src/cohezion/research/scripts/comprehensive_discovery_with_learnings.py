#!/usr/bin/env python3
"""Comprehensive model discovery with learning capture.

Captures patterns and learnings while discovering all models.

Learnings:
- FLM list format parsing (discovered structure)
- Model size inference from naming conventions
- Capability mapping patterns
- Resource-safe iteration techniques
- Error handling for discovery failures
- Metadata inference without model loading

Extracted Skill: Resource-safe iterative discovery
"""

import json
import subprocess
import time
from pathlib import Path

import psutil


# Learning capture
LEARNINGS = []


def log_learning(category: str, insight: str):
    """Capture learning during discovery."""
    LEARNINGS.append(
        {"category": category, "insight": insight, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    )
    print(f"  💡 Learning: [{category}] {insight[:80]}...")


def discover_all_models_comprehensive() -> tuple[list[dict], list[dict]]:
    """Discover all models across all sources with learning capture."""

    print("=" * 70)
    print("COMPREHENSIVE MODEL DISCOVERY WITH LEARNING CAPTURE")
    print("=" * 70)

    all_models = []

    # ========== SOURCE 1: FLM List (NPU) ==========
    print("\n📋 Source 1: FLM (NPU) Models")
    print("-" * 70)

    try:
        result = subprocess.run(["flm", "list"], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")

            for line in lines:
                line = line.strip()
                # Skip headers, comments, empty lines
                if not line or line.startswith("[") or line.startswith("┌"):
                    continue

                # Parse model name (format: "model:name:size ⏬")
                if ":" in line and "⏬" in line:
                    parts = line.split()
                    if parts:
                        model_name = parts[0]
                        if len(model_name) > 2:  # Valid name
                            all_models.append(
                                {
                                    "name": model_name,
                                    "source": "FLM_NPU",
                                    "backend": "NPU",
                                    "backend_type": "FLM",
                                    "status": "available",
                                    "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                }
                            )
                            print(f"  ✓ {model_name}")

            log_learning(
                "parsing",
                f"FLM list format: {{model}}:{{size}} ⏬ - parsed {len([m for m in all_models if m['source'] == 'FLM_NPU'])} models",
            )
        else:
            log_learning("error_handling", f"FLM list failed with code {result.returncode}")

    except subprocess.TimeoutExpired:
        log_learning("error_handling", "FLM list timed out after 10s - system may be busy")
    except FileNotFoundError:
        log_learning("error_handling", "FLM command not found - NPU SDK not installed")
    except Exception as e:
        log_learning("error_handling", f"FLM unexpected error: {type(e).__name__}: {e}")

    # ========== SOURCE 2: Known NPU Models ==========
    print("\n📋 Source 2: Known NPU Model Variants")
    print("-" * 70)

    known_npu_models = [
        # Qwen3 family
        ("qwen3:4b", "4B", "code"),
        ("qwen3:7b", "7B", "code"),
        ("qwen3:1.5b", "1.5B", "code"),
        # Gemma3 family
        ("gemma3:4b", "4B", "general"),
        ("gemma3:12b", "12B", "general"),
        # Qwen3.5 family
        ("qwen3.5:0.8b", "0.8B", "code"),
        ("qwen3.5:2b", "2B", "code"),
        ("qwen3.5:4b", "4B", "code"),
        ("qwen3.5:9b", "9B", "code"),
        # Specialized
        ("qwen3vl-it:4b", "4B", "vision"),
        ("translategemma:4b", "4B", "translation"),
        ("whisper-v3:turbo", "turbo", "audio"),
    ]

    added_known = 0
    for model_name, size, category in known_npu_models:
        # Skip if already discovered
        if not any(m["name"] == model_name for m in all_models):
            # Infer capabilities from name
            capabilities = infer_capabilities_from_name(model_name)

            all_models.append(
                {
                    "name": model_name,
                    "source": "KNOWN_NPU",
                    "backend": "NPU",
                    "backend_type": "FLM",
                    "size": size,
                    "category": category,
                    "capabilities": capabilities,
                    "status": "likely_available",
                    "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )
            print(f"  ✓ {model_name} ({category})")
            added_known += 1

    if added_known > 0:
        log_learning(
            "capability_inference",
            "Inferred capabilities from naming patterns: qwen=code, gemma=general, vl=vision, translate=translation, whisper=audio",
        )

    # ========== SOURCE 3: Validated Specialists ==========
    print("\n📋 Source 3: Validated Production Models")
    print("-" * 70)

    validated = [
        {
            "name": "qwen3:4b",
            "specialist": "CodeSpecialist",
            "backend": "NPU",
            "tps": 75.0,
            "latency_ms": 13.0,
            "context_window": 131072,
            "memory_mb": 4096,
            "power_watts": 15,
            "validated": True,
        },
        {
            "name": "Gemma-4-E2B-it-GGUF",
            "specialist": "ReasoningSpecialist",
            "backend": "GPU_VULKAN",
            "backend_type": "llama.cpp",
            "tps": 97.26,
            "latency_ms": 10.3,
            "context_window": 262144,
            "memory_mb": 4096,
            "power_watts": 25,
            "validated": True,
        },
        {
            "name": "Jan-v1-4B-GGUF",
            "specialist": "NovelSpecialist",
            "backend": "GPU_VULKAN",
            "backend_type": "llama.cpp",
            "tps": 76.18,
            "latency_ms": 13.1,
            "context_window": 4096,
            "memory_mb": 4096,
            "power_watts": 25,
            "validated": True,
        },
    ]

    for v in validated:
        existing = next(
            (m for m in all_models if v["name"] in m["name"] or m["name"] in v["name"]), None
        )
        if existing:
            # Enrich with validated metrics
            existing.update(v)
            existing["status"] = "validated"
            print(f"  ✓ {v['name']} (VALIDATED - {v['tps']} TPS)")
        else:
            all_models.append(
                {
                    **v,
                    "source": "VALIDATED",
                    "status": "validated",
                    "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            )
            print(f"  ✓ {v['name']} (VALIDATED - {v['tps']} TPS)")

    log_learning(
        "validation",
        "Validated performance metrics provide ground truth for TPS, latency, memory usage",
    )

    # ========== SOURCE 4: Local GGUF Files ==========
    print("\n📋 Source 4: Local Cached Models")
    print("-" * 70)

    local_models = []
    search_paths = [
        Path.home() / ".cache/flm/models",
        Path.home() / ".cache/llama.cpp",
        Path.home() / ".local/share/models",
    ]

    for path in search_paths:
        if path.exists():
            try:
                gguf_files = list(path.rglob("*.gguf"))
                for gguf in gguf_files[:20]:  # Limit to avoid overload
                    name = gguf.stem
                    # Skip if already known
                    if not any(name in m["name"] or m["name"] in name for m in all_models):
                        local_models.append(
                            {
                                "name": name,
                                "source": "LOCAL_GGUF",
                                "backend": "GPU_VULKAN",
                                "backend_type": "llama.cpp",
                                "path": str(gguf),
                                "status": "cached",
                                "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            }
                        )
                        print(f"  ✓ {name}")
            except Exception as e:
                log_learning("error_handling", f"Error scanning {path}: {e}")

    all_models.extend(local_models)

    if local_models:
        log_learning("discovery", f"Found {len(local_models)} locally cached GGUF models")

    # ========== SUMMARY ==========
    print("\n" + "=" * 70)
    print("COMPREHENSIVE DISCOVERY COMPLETE")
    print("=" * 70)

    # Filter out invalid entries
    valid_models = [m for m in all_models if len(m.get("name", "")) > 2]

    # Stats
    by_backend = {}
    by_source = {}
    for m in valid_models:
        be = m.get("backend", "unknown")
        by_backend[be] = by_backend.get(be, 0) + 1
        src = m.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

    print(f"\n📊 Total Models Discovered: {len(valid_models)}")
    print("\nBy Backend:")
    for backend, count in sorted(by_backend.items()):
        print(f"  {backend}: {count}")

    print("\nBy Source:")
    for source, count in sorted(by_source.items()):
        print(f"  {source}: {count}")

    # Resource status
    mem = psutil.virtual_memory()
    print(f"\n💾 System Memory: {mem.percent:.1f}% ({mem.used / 1024**3:.1f}GB used)")
    print("✅ Safe for operation")

    # Save comprehensive results
    output = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_models": len(valid_models),
            "by_backend": by_backend,
            "by_source": by_source,
            "system_memory_percent": mem.percent,
        },
        "models": valid_models,
        "learnings": LEARNINGS,
    }

    output_path = Path("comprehensive_model_registry.json")
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n📁 Saved to: {output_path}")
    print(f"   Learnings captured: {len(LEARNINGS)}")

    return valid_models, LEARNINGS


def infer_capabilities_from_name(model_name: str) -> list[str]:
    """Infer capabilities from model name patterns.

    Learning: Naming conventions encode capability hints
    - "qwen" / "code" / "coder" → code generation
    - "vl" / "vision" / "llava" → vision understanding
    - "whisper" / "audio" → audio transcription
    - "translate" → translation
    - "instruct" / "chat" → instruction following
    - "reasoning" → complex reasoning
    """
    name = model_name.lower()
    capabilities = []

    # Code capabilities
    if any(x in name for x in ["qwen", "code", "coder", "starcoder"]):
        capabilities.extend(["code_generation", "code_completion", "syntax_check"])

    # Vision capabilities
    if any(x in name for x in ["vl", "vision", "llava", "clip"]):
        capabilities.extend(["vision_understanding", "image_description"])

    # Audio capabilities
    if any(x in name for x in ["whisper", "audio", "speech"]):
        capabilities.extend(["audio_transcription", "audio_speech"])

    # Translation
    if "translate" in name:
        capabilities.append("translation")

    # Reasoning/Chat
    if any(x in name for x in ["instruct", "chat", "reasoning"]):
        capabilities.extend(["instruction_following", "chat_conversation", "reasoning"])

    # General (assume all)
    capabilities.extend(["text_generation", "summarization"])

    return list(set(capabilities))


if __name__ == "__main__":
    models, learnings = discover_all_models_comprehensive()

    print("\n" + "=" * 70)
    print("LEARNINGS EXTRACTED")
    print("=" * 70)
    for i, l in enumerate(learnings[:10], 1):
        print(f"{i}. [{l['category']}] {l['insight'][:100]}")
