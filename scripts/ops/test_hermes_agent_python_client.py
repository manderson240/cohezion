#!/usr/bin/env python3
"""Direct Python OpenAI SDK test matching Hermes Agent client internals against Lemonade Router."""

import time

from openai import OpenAI


client = OpenAI(
    base_url="http://localhost:13305/api/v1",
    api_key="lemonade"
)

print("1. Testing non-streaming completion with tools...")
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_system_time",
            "description": "Get current timestamp",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

t0 = time.perf_counter()
resp = client.chat.completions.create(
    model="user.cohezion-hermes-router",
    messages=[
        {"role": "system", "content": "You are Hermes Agent with tools enabled."},
        {"role": "user", "content": "What time is it right now? Use the tool."}
    ],
    tools=tools,
    max_tokens=150
)
dt = time.perf_counter() - t0
print(f"✓ Completed in {dt:.2f}s:")
choice = resp.choices[0].message
print("  Role:", choice.role)
print("  Content:", choice.content)
print("  Tool Calls:", choice.tool_calls)

print("\n2. Testing streaming completion...")
t0 = time.perf_counter()
stream = client.chat.completions.create(
    model="user.cohezion-hermes-router",
    messages=[
        {"role": "system", "content": "You are Hermes Agent."},
        {"role": "user", "content": "Count from 1 to 5."}
    ],
    max_tokens=50,
    stream=True
)
print("  Streaming output: ", end="", flush=True)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print(f"\n✓ Stream completed in {time.perf_counter() - t0:.2f}s")
