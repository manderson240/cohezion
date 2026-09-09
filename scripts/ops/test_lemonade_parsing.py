import httpx
import json

payload = {
    "model": "gpt-oss-20b",
    "messages": [
        {"role": "user", "content": "Write a python function `def transform(grid): return grid[::-1]` in a python code block."}
    ],
    "max_tokens": 150
}

r = httpx.post("http://localhost:13305/v1/chat/completions", json=payload, timeout=30.0)
print("Status:", r.status_code)
msg = r.json()["choices"][0]["message"]
print("Message Keys:", list(msg.keys()))
print("Content:", repr(msg.get("content")))
print("Thinking (if any):", repr(msg.get("reasoning_content") or msg.get("thinking")))
