"""Reliability/offload MCP tools (claim resolution, SLM offload, batch, cache).

These wrap the ``cohezion.reliability`` subsystem behind MCP-friendly,
``content``-style envelopes. The resolver/offloader instances are passed in
from the server to keep dependency wiring explicit and testable.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


def resolve_claims(text: str, resolver: Any) -> dict[str, Any]:
    """Run the hallucination resolver over ``text`` and return its JSON report."""
    if not resolver:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Error: HallucinationResolver not available",
                }
            ]
        }
    res = resolver.resolve_claims(text)
    return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}


def offload_task(
    query: str,
    system_prompt: str | None,
    offloader: Any,
    context_harness_cls: Any,
) -> dict[str, Any]:
    """Offload ``query`` to a local SLM if the offloader recommends it.

    Refuses offload (returning a text envelope) when the task is judged too
    complex/critical. Otherwise harnesses the prompt with ``context_harness_cls``
    and POSTs to the local Ollama API.
    """
    if not offloader:
        return {"content": [{"type": "text", "text": "Error: OffloadManager not available"}]}

    recommendation = offloader.get_offload_recommendation(query)
    if not recommendation["offload"]:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "Task unsuitable for local offload (too complex or critical).",
                }
            ]
        }

    target_model = recommendation["target"]
    harness = context_harness_cls(target_model=target_model)
    payload = harness.harness_prompt(query, system_prompt)

    # Execute via Ollama API using curl for robustness
    try:
        payload_json = json.dumps(
            {
                "model": target_model,
                "prompt": payload["prompt"],
                "system": payload["system"],
                "stream": False,
            }
        )
        cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            "http://localhost:11434/api/generate",
            "-d",
            payload_json,
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return {"content": [{"type": "text", "text": f"Curl failed: {res.stderr}"}]}

        try:
            res_json = json.loads(res.stdout)
            res_text = res_json.get("response", "")
            return {"content": [{"type": "text", "text": res_text}]}
        except json.JSONDecodeError:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Failed to parse response: {res.stdout}",
                    }
                ]
            }
    except (
        OSError,
        ValueError,
        KeyError,
        AttributeError,
        ImportError,
    ) as e:
        return {"content": [{"type": "text", "text": f"Offload execution failed: {e}"}]}


def batch_offload(tasks: list[dict[str, Any]], model: str | None = None) -> dict[str, Any]:
    """Bundle several SLM tasks into one Ollama call via ``BatchManager``."""
    from cohezion.reliability.batch_manager import BatchManager
    from cohezion.reliability.context_harness import ContextHarness

    target_model = model or "phi4"
    batch_mgr = BatchManager()
    for t in tasks:
        batch_mgr.enqueue(t["id"], t["query"], t.get("context"))

    batch = batch_mgr.get_batch()
    if not batch:
        return {"content": [{"type": "text", "text": "No tasks to batch."}]}

    harness = ContextHarness(target_model=target_model)
    payload = harness.harness_prompt(batch["prompt"])

    try:
        payload_json = json.dumps(
            {
                "model": target_model,
                "prompt": payload["prompt"],
                "system": payload["system"],
                "stream": False,
            }
        )
        cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            "http://localhost:11434/api/generate",
            "-d",
            payload_json,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        res_json = json.loads(res.stdout)
        res_text = res_json.get("response", "")

        results = batch_mgr.parse_batch_response(res_text)
        return {"content": [{"type": "text", "text": json.dumps(results, indent=2)}]}
    except (
        OSError,
        ValueError,
        KeyError,
        AttributeError,
        ImportError,
    ) as e:
        return {"content": [{"type": "text", "text": f"Batch offload failed: {e}"}]}


def inspect_cache() -> dict[str, Any]:
    """Return ``SemanticCache`` hit-rate and population statistics."""
    from cohezion.reliability.semantic_cache import SemanticCache

    # Using a default instance for inspection
    cache = SemanticCache()
    stats = cache.get_stats()
    return {"content": [{"type": "text", "text": json.dumps(stats, indent=2)}]}