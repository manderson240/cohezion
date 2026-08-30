import urllib.request
import json

# Send the 15464 token prompt to each candidate model in Lemonade to see which one throws 8192
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

candidates = [
    "gpt-oss-20b-mxfp4-GGUF",
    "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "qwen3.6-moe-35b-a3b-FLM",
    "deepseek-r1-0528-8b-FLM",
    "waslmedia-qwen3-4b-Q4_K_M"
]

for m in candidates:
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
            print(f"✓ {m:35} -> HTTP {resp.status} (ACCEPTED)")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        print(f"✗ {m:35} -> HTTP {e.code}: {body.strip()}")
    except Exception as e:
        print(f"✗ {m:35} -> Error: {e}")
