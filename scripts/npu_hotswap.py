#!/usr/bin/env python3
"""CLI utility for managing and verifying on-demand model hotswapping on the AMD XDNA 2 NPU.

Usage:
    python3 scripts/npu_hotswap.py list
    python3 scripts/npu_hotswap.py active
    python3 scripts/npu_hotswap.py swap <model_name>
    python3 scripts/npu_hotswap.py query <model_name> "<prompt>"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path


# Add project root to sys.path
WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE))

from cohezion.inference.hotswap import (  # noqa: E402
    LEMONADE_BASE,
    ensure_resident,
    resident_models,
)


NPU_CATALOG = {
    "deepseek-r1-0528-8b-FLM": {
        "checkpoint": "deepseek-r1-0528:8b",
        "description": "DeepSeek R1 Reasoning (thinking tokens, formal logic, invariants)",
        "size_gb": 5.6,
        "type": "reasoning",
    },
    "qwen3.5-4b-FLM": {
        "checkpoint": "qwen3.5:4b",
        "description": "Qwen 3.5 4B Instruction / Code generation (fast, zero UMA)",
        "size_gb": 5.0,
        "type": "instruction",
    },
    "qwen3vl-it-4b-FLM": {
        "checkpoint": "qwen3vl-it:4b",
        "description": "Qwen 3 Vision-Language multimodal agent (ARC grid vision)",
        "size_gb": 3.9,
        "type": "vision",
    },
    "gemma4-it-e2b-FLM": {
        "checkpoint": "gemma4-it:e2b",
        "description": "Google Gemma 4 instruction model on NPU",
        "size_gb": 6.0,
        "type": "instruction",
    },
    "embed-gemma-300m-FLM": {
        "checkpoint": "embed-gemma:300m",
        "description": "Gemma 300M Dense Semantic Embeddings",
        "size_gb": 0.62,
        "type": "embedding",
    },
    "llama3.2-1b-FLM": {
        "checkpoint": "llama3.2:1b",
        "description": "Llama 3.2 1B ultra-lightweight edge fallback",
        "size_gb": 1.3,
        "type": "edge",
    },
}


def cmd_list(args: argparse.Namespace) -> int:
    """List resident and available models."""
    print("=" * 72)
    print("AMD XDNA 2 NPU & CPU FLEET STATUS")
    print("=" * 72)

    loaded = resident_models()
    resident_names = {m.get("model_name"): m for m in loaded}

    print("\n[RESIDENT MODELS]")
    if not loaded:
        print("  No models currently resident.")
    else:
        for m in loaded:
            name = m.get("model_name", "unknown")
            dev = m.get("device", "cpu").upper()
            busy = "BUSY" if m.get("is_busy") else "IDLE"
            recipe = m.get("recipe", "unknown")
            print(f"  * {name:<26} [Device: {dev:<4} | Status: {busy:<4} | Recipe: {recipe}]")

    print("\n[AVAILABLE NPU FASTFLOWLM CATALOG]")
    for model_id, info in NPU_CATALOG.items():
        is_active = "[ACTIVE]" if model_id in resident_names else "        "
        print(f"  {is_active} {model_id:<26} ({info['size_gb']:>4.1f} GB) - {info['description']}")

    print("=" * 72)
    return 0


def cmd_active(args: argparse.Namespace) -> int:
    """Print the currently resident NPU model."""
    loaded = resident_models()
    for m in loaded:
        if m.get("device", "").lower() == "npu":
            print(m.get("model_name"))
            return 0
    print("none")
    return 1


def cmd_swap(args: argparse.Namespace) -> int:
    """Hotswap the active NPU model."""
    target = args.model
    if not target.endswith("-FLM") and f"{target}-FLM" in NPU_CATALOG:
        target = f"{target}-FLM"

    print(f"[HOTSWAP] Requesting resident transition to '{target}'...")
    start_t = time.time()
    res = ensure_resident(
        target,
        ctx_size=args.ctx_size,
        load_timeout=120.0,
        verify_retries=6,
        verify_delay_s=1.0,
    )
    elapsed = time.time() - start_t

    if res.ok:
        status_str = "ALREADY RESIDENT" if res.already_resident else "SUCCESSFULLY LOADED"
        print(f"[HOTSWAP] {status_str} in {elapsed:.2f}s!")
        print(f"  Model:   {res.model_id}")
        print(f"  Reason:  {res.reason}")
        if res.evicted:
            print(f"  Evicted: {', '.join(res.evicted)}")
        return 0
    else:
        print(f"[HOTSWAP] FAILED in {elapsed:.2f}s:")
        print(f"  Model:   {res.model_id}")
        print(f"  Reason:  {res.reason}")
        if res.evicted:
            print(f"  Evicted: {', '.join(res.evicted)}")
        return 1


def cmd_query(args: argparse.Namespace) -> int:
    """Query an NPU model, hotswapping on demand if necessary."""
    target = args.model
    if not target.endswith("-FLM") and f"{target}-FLM" in NPU_CATALOG:
        target = f"{target}-FLM"

    print(f"[QUERY] Ensuring '{target}' is resident on NPU...")
    swap_res = ensure_resident(
        target,
        ctx_size=args.ctx_size,
        load_timeout=120.0,
        verify_retries=6,
        verify_delay_s=1.0,
    )
    if not swap_res.ok:
        print(f"[QUERY] Hotswap failure: {swap_res.reason}")
        return 1

    payload = {
        "model": target,
        "messages": [
            {"role": "user", "content": args.prompt},
        ],
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }

    print(f"[QUERY] Dispatching prompt to {target} via {LEMONADE_BASE}...")
    start_t = time.time()
    req = urllib.request.Request(  # noqa: S310
        f"{LEMONADE_BASE}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120.0) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - start_t
            choice = data.get("choices", [{}])[0].get("message", {})
            content = choice.get("content", "").strip()
            reasoning = choice.get("reasoning_content", "").strip()
            usage = data.get("usage", {})

            print(
                f"\n[RESPONSE] (Generated in {elapsed:.2f}s | {usage.get('total_tokens', 0)} tokens)"
            )
            if reasoning:
                print("\n--- [Thinking / Reasoning Trace] ---")
                print(reasoning)
                print("------------------------------------")
            if content:
                print("\n--- [Output Content] ---")
                print(content)
                print("------------------------")
            return 0
    except Exception as e:
        print(f"[QUERY] Error communicating with gateway: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Cohezion NPU Model Hotswapping CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List resident and available NPU models")
    p_list.set_defaults(func=cmd_list)

    # active
    p_active = subparsers.add_parser("active", help="Print active NPU model")
    p_active.set_defaults(func=cmd_active)

    # swap
    p_swap = subparsers.add_parser("swap", help="Hotswap to specified model")
    p_swap.add_argument("model", help="Target model ID or prefix")
    p_swap.add_argument("--ctx-size", type=int, default=16384, help="Context size limit")
    p_swap.set_defaults(func=cmd_swap)

    # query
    p_query = subparsers.add_parser("query", help="Query a model with demand-driven hotswap")
    p_query.add_argument("model", help="Target model ID")
    p_query.add_argument("prompt", help="Prompt string")
    p_query.add_argument("--max-tokens", type=int, default=512, help="Max tokens")
    p_query.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    p_query.add_argument("--ctx-size", type=int, default=16384, help="Context size")
    p_query.set_defaults(func=cmd_query)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
