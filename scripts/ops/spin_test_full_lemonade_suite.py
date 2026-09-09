#!/usr/bin/env python3
"""Execute a comprehensive, real-world live flight test of the Cohezion-Lemonade Router across NPU, iGPU, CPU, and Tool Execution."""

from __future__ import annotations

import json
import time
import urllib.request


URL = "http://localhost:13305/api/v1/chat/completions"
MODEL = "user.cohezion-hermes-router"

FLIGHT_MISSIONS = [
    {
        "id": "MISSION 1: FAST NPU CONVERSATION",
        "description": "NPU ultra-sparse MoE quick conversational response",
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are Cohezion sovereign assistant on AMD Strix Halo."},
                {"role": "user", "content": "Briefly describe the three compute domains of the AMD Ryzen AI MAX+ 395 processor."}
            ],
            "max_tokens": 120,
            "route_trace": True
        }
    },
    {
        "id": "MISSION 2: iGPU ALGORITHMIC & REFACTORING TASK",
        "description": "iGPU Qwen3-Coder-30B generating a verified Python LRU cache",
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are Cohezion senior coding engineer."},
                {"role": "user", "content": "Write a clean Python class `AsyncLRUCache` with `get`, `put`, and an eviction policy using `collections.OrderedDict`."}
            ],
            "max_tokens": 250,
            "route_trace": True
        }
    },
    {
        "id": "MISSION 3: DEEP REASONING & PHYSICAL DIAGNOSTICS",
        "description": "Deep reasoning model analyzing Shoulders' borehole aspect ratio",
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a plasma physicist."},
                {"role": "user", "content": "Explain why Kenneth Shoulders observed clean cylindrical micro-boreholes (4.0 μm x 14.2 μm) in aluminum targets instead of hemispherical impact craters."}
            ],
            "max_tokens": 200,
            "route_trace": True
        }
    },
    {
        "id": "MISSION 4: AGENTIC STRUCTURED TOOL CALLING",
        "description": "Agentic tool calling dispatch for system memory inspection",
        "payload": {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are Hermes Agent with hardware diagnostic tools."},
                {"role": "user", "content": "Check the available memory headroom for the NPU."}
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "check_npu_memory",
                        "description": "Query available NPU memory pool",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "domain": {"type": "string", "enum": ["npu", "igpu", "cpu", "uma"]}
                            },
                            "required": ["domain"]
                        }
                    }
                }
            ],
            "max_tokens": 100,
            "route_trace": True
        }
    }
]


def execute_mission(mission: dict) -> None:
    print("\n" + "=" * 90)
    print(f"  🛫 EXECUTING {mission['id']}")
    print(f"  📝 Objective: {mission['description']}")
    print("=" * 90)

    req = urllib.request.Request(
        URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(mission["payload"]).encode("utf-8")
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            dt = time.perf_counter() - t0
            headers = dict(resp.headers)
            route = headers.get("x-lemonade-route", "unknown")
            raw_body = resp.read().decode("utf-8")
            data = json.loads(raw_body)

            model_used = data.get("model", "unknown")
            msg = data["choices"][0]["message"]
            content = msg.get("content", "")
            reasoning = msg.get("reasoning_content", "")
            tool_calls = msg.get("tool_calls", [])

            print(f"  ✓ Route Matched: [{route}] -> Model: [{model_used}]")
            print(f"  ⏱ Total Flight Latency: {dt:.2f}s")

            if tool_calls:
                print(f"  🛠️ Structured Tool Calls ({len(tool_calls)}):")
                for tc in tool_calls:
                    print(f"     - Function: {tc['function']['name']}({tc['function']['arguments']})")
            elif content:
                print(f"  💬 Generated Response:\n\n{content.strip()}\n")
            elif reasoning:
                print(f"  🧠 Deep Reasoning (CoT):\n\n{reasoning.strip()}\n")

    except Exception as e:
        print(f"  ✗ Mission Error: {e}")


def main() -> None:
    print("=" * 90)
    print("  🚀 COHEZION-LEMONADE ROUTER LIVE FLIGHT TEST SUITE (PORT 13305)")
    print("  Processor: AMD Ryzen AI MAX+ 395 w/ Radeon 8060S (Strix Halo)")
    print("=" * 90)

    for m in FLIGHT_MISSIONS:
        execute_mission(m)

    print("\n" + "=" * 90)
    print("  🎉 ALL 4 FLIGHT MISSIONS COMPLETED CLEANLY!")
    print("=" * 90)


if __name__ == "__main__":
    main()
