#!/usr/bin/env python3
"""Verify Hermes Desktop router policy with agentic tools routing to Qwen3-Coder-30B."""

import json
import time
import urllib.request


url = "http://127.0.0.1:13305/v1/chat/completions"

# 1. Test conversational turn (without tools)
payload_chat = {
    "model": "user.cohezion-router",
    "messages": [
        {"role": "system", "content": "You are Hermes Desktop Assistant."},
        {"role": "user", "content": "Say hello in 3 words."}
    ],
    "max_tokens": 20,
    "stream": True
}

print("1. Testing Chat Turn on user.cohezion-router...")
req_chat = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload_chat).encode())
t0 = time.perf_counter()
first_token = None
output_text = ""

try:
    with urllib.request.urlopen(req_chat, timeout=15) as resp:
        for line in resp:
            l = line.decode('utf-8').strip()
            if l.startswith("data: ") and l != "data: [DONE]":
                d = json.loads(l[6:])
                delta = d["choices"][0]["delta"]
                tok = delta.get("content") or delta.get("reasoning_content") or ""
                if tok:
                    if first_token is None:
                        first_token = time.perf_counter() - t0
                    output_text += tok
    print(f"✓ Chat Response: '{output_text.strip()}' (TTFT: {first_token:.2f}s, Total: {time.perf_counter() - t0:.2f}s)")
except Exception as e:
    print(f"✗ Chat failed: {e}")

# 2. Test tool-carrying turn
payload_tools = {
    "model": "user.cohezion-router",
    "messages": [
        {"role": "system", "content": "You are Hermes Desktop Assistant."},
        {"role": "user", "content": "Check the local time."}
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "Get current system time",
                "parameters": {"type": "object", "properties": {}}
            }
        }
    ],
    "max_tokens": 40
}

print("\n2. Testing Agentic Tool Turn on user.cohezion-router...")
req_tools = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload_tools).encode())
t0 = time.perf_counter()

try:
    with urllib.request.urlopen(req_tools, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        route = resp.headers.get("x-lemonade-route", "unknown")
        tools = data["choices"][0]["message"].get("tool_calls", [])
        tool_name = tools[0]["function"]["name"] if tools else "None"
        print(f"✓ Tool Call Dispatched: '{tool_name}' in {time.perf_counter() - t0:.2f}s (Route: {route})")
except Exception as e:
    print(f"✗ Tool test failed: {e}")
