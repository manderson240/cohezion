"""Model selection, benchmarking, and compound config tools for the MCP server.

These handlers operate on the in-memory model registry plus optional
``ResourceMonitor`` vitals; they never call out to network APIs (except a
local ``ollama list`` shell call in :func:`select_model`).
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any


def elite_model_selection(args: dict[str, Any], model_registry: dict[str, Any]) -> dict[str, Any]:
    """Pick the best registered model for ``args['task_type']`` under a memory cap.

    Sorts candidates by ``performance_priority`` (accuracy/memory-efficiency/
    balanced). Falls back to ``phi4-256k:latest`` when no candidate fits.
    """
    try:
        task_type = args.get("task_type", "coding")
        memory_available = args.get("memory_available", 125)
        context_needs = args.get("context_needs", 32768)
        performance_priority = args.get("performance_priority", "balanced")

        models = model_registry.get("models", {})

        # Filter models by task specialization and memory constraints
        candidates = []
        for model_id, model_info in models.items():
            if task_type in model_info.get("specialization", "") or task_type in model_id:
                model_memory = model_info.get("memory", 0)
                if model_memory <= memory_available:
                    candidates.append((model_id, model_info))

        # Sort by priority and performance
        if performance_priority == "accuracy":
            candidates.sort(key=lambda x: (-x[1].get("priority", 99), x[1].get("memory", 999)))
        elif performance_priority == "memory-efficiency":
            candidates.sort(key=lambda x: (x[1].get("memory", 999), -x[1].get("priority", 99)))
        else:  # balanced
            candidates.sort(key=lambda x: (x[1].get("priority", 99), x[1].get("memory", 999)))

        recommended_model = candidates[0][0] if candidates else "phi4-256k:latest"

        selection_result = {
            "recommended_model": recommended_model,
            "task_type": task_type,
            "memory_available": memory_available,
            "context_needs": context_needs,
            "performance_priority": performance_priority,
            "candidates": [{"id": m[0], "info": m[1]} for m in candidates[:3]],
            "optimization_applied": {
                "moe_aware": "qwen3-coder-next" in recommended_model,
                "ocr_optimized": "glm-ocr" in recommended_model,
                "memory_aware": memory_available < 90,
            },
        }

        return {"content": [{"type": "text", "text": json.dumps(selection_result, indent=2)}]}

    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
    ) as e:
        return {"content": [{"type": "text", "text": f"Elite model selection failed: {e}"}]}


def performance_benchmark(args: dict[str, Any]) -> dict[str, Any]:
    """Return canned benchmark numbers for the requested elite models.

    Currently a mock implementation: returns hard-coded inference speed,
    memory usage, and accuracy for known model families. Real benchmarking
    is delegated to upstream tooling.
    """
    try:
        models = args.get(
            "models",
            ["qwen3-coder-next:q8_0", "qwen3-coder-next:latest", "glm-ocr:latest"],
        )
        benchmark_types = args.get("benchmark_types", ["inference-speed", "memory-usage"])
        iterations = args.get("iterations", 3)

        benchmark_results = {}

        for model in models:
            model_results = {}

            # Mock benchmark results for demonstration
            if "qwen3-coder-next:q8_0" in model:
                model_results = {
                    "inference_speed": "2.3 tokens/sec",
                    "memory_usage": "84GB",
                    "accuracy": "70.6% SWE-Bench",
                    "token_efficiency": "96.25% (3B/80B active)",
                }
            elif "qwen3-coder-next:latest" in model:
                model_results = {
                    "inference_speed": "3.1 tokens/sec",
                    "memory_usage": "51GB",
                    "accuracy": "70.6% SWE-Bench",
                    "token_efficiency": "96.25% (3B/80B active)",
                }
            elif "glm-ocr" in model:
                model_results = {
                    "inference_speed": "5.8 tokens/sec",
                    "memory_usage": "2.2GB",
                    "accuracy": "94.62% OmniDocBench",
                    "token_efficiency": "Optimized for documents",
                }

            benchmark_results[model] = model_results

        report = {
            "benchmark_timestamp": "2026-02-04",
            "models_tested": models,
            "benchmark_types": benchmark_types,
            "iterations": iterations,
            "results": benchmark_results,
            "summary": {
                "fastest_inference": "glm-ocr:latest",
                "most_accurate": "glm-ocr:latest",
                "most_memory_efficient": "glm-ocr:latest",
                "best_overall": "qwen3-coder-next:q8_0",
            },
        }

        return {"content": [{"type": "text", "text": json.dumps(report, indent=2)}]}

    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
    ) as e:
        return {"content": [{"type": "text", "text": f"Performance benchmark failed: {e}"}]}


def get_compound_config(
    compound_config: dict[str, Any],
    model_registry: dict[str, Any],
    monitor: Any,
) -> dict[str, Any]:
    """Bundle compound settings, model registry, and live system vitals."""
    vitals = monitor.get_vitals() if monitor else {"status": "monitor_not_available"}
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "config": compound_config,
                        "models": model_registry.get("models", {}),
                        "vitals": vitals,
                    },
                    indent=2,
                ),
            }
        ]
    }


def select_model(
    task_type: str,
    complexity: int,
    context_needs: int,
    model_registry: dict[str, Any],
) -> dict[str, Any]:
    """Pick a model whose specialization matches ``task_type`` and is installed.

    Cross-references the registry against ``ollama list`` so we don't recommend
    an absent model. Falls back to a hard-coded preference list if no specialist
    is installed.
    """
    models = model_registry.get("models", {})

    # Pre-flight check: which models are actually in Ollama?
    installed_models = set()
    try:
        res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        for line in res.stdout.splitlines()[1:]:  # Skip header
            if line.strip():
                installed_models.add(line.split()[0].split(":")[0])  # Base name
    except (OSError, subprocess.SubprocessError) as e:
        sys.stderr.write(f"Failed to check installed models: {e}\n")

    # Flatten models for selection
    flat_models = {}
    for category in models.values():
        if isinstance(category, dict):
            flat_models.update(category)

    # Filter candidates by specialization AND installation status
    candidates = []
    for m_id, m_info in flat_models.items():
        if not isinstance(m_info, dict):
            continue
        base_id = m_id.split(":")[0]
        if m_info.get("specialization") == task_type:
            if base_id in installed_models:
                candidates.append((base_id, m_info))
            else:
                sys.stderr.write(f"Warning: Specialist model {base_id} not installed in Ollama.\n")

    if candidates:
        candidates.sort(key=lambda x: x[1].get("priority", 99))
        recommended = candidates[0][0]
    else:
        # Fallback to the most capable installed model
        fallback_order = [
            "qwen3-coder-next",
            "qwen3-coder-256k",
            "gpt-oss-256k",
            "phi4-256k",
            "phi4-mini",
        ]
        recommended = next((m for m in fallback_order if m in installed_models), "phi4-mini")

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "recommended_model": f"{recommended}:latest",
                        "all_models": [f"{m}:latest" for m in models],
                        "installed_only": list(installed_models),
                    },
                    indent=2,
                ),
            }
        ]
    }
