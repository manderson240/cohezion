import urllib.request
import json
import time

url = "http://127.0.0.1:13305/v1/chat/completions"

# System prompt + tool schema payload that Hermes Agent sends
tools = [
    {
        "type": "function",
        "function": {
            "name": f"tool_{i}",
            "description": f"Tool description {i} for agent capabilities",
            "parameters": {
                "type": "object",
                "properties": {
                    "param": {"type": "string", "description": "some input"}
                }
            }
        }
    }
    for i in range(45)
]

payload = {
    "model": "gpt-oss-20b-mxfp4-GGUF",
    "messages": [
        {"role": "system", "content": "You are Hermes Agent on Strix Halo with tools."},
        {"role": "user", "content": "Status update"}
    ],
    "tools": tools,
    "max_tokens": 4096,
    "stream": True
}

print(f"Sending 45-tool streaming request to {url}...")
req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
t0 = time.perf_counter()

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        for line in resp:
            l = line.decode('utf-8').strip()
            if l.startswith("data: ") and l != "data: [DONE]":
                d = json.loads(l[6:])
                delta = d["choices"][0]["delta"]
                tok = delta.get("content") or delta.get("reasoning_content") or ""
                if tok:
                    print(tok, end="", flush=True)
        print(f"\n✓ Completed in {time.perf_counter() - t0:.2f}s")
except Exception as e:
    print(f"\n✗ Error: {e}")
