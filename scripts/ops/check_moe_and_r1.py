import urllib.request
import json

tools = [
    {
        "type": "function",
        "function": {
            "name": f"tool_{i}",
            "description": f"Tool description {i}",
            "parameters": {"type": "object", "properties": {"param": {"type": "string"}}}
        }
    }
    for i in range(45)
]

for m in ["qwen3.6-moe-35b-a3b-FLM", "waslmedia-qwen3-4b-Q4_K_M"]:
    url = "http://127.0.0.1:13305/v1/chat/completions"
    payload = {
        "model": m,
        "messages": [
            {"role": "system", "content": "You are Hermes Agent with tools."},
            {"role": "user", "content": "Status update"}
        ],
        "tools": tools,
        "max_tokens": 10
    }
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"✓ {m:30} -> HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        print(f"✗ {m:30} -> HTTP {e.code}: {body.strip()}")
    except Exception as e:
        print(f"✗ {m:30} -> Error: {e}")
