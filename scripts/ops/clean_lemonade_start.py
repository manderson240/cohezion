import json
import time
import urllib.request


url_pull = "http://127.0.0.1:13305/api/v1/pull"

# Define a clean router policy where every request maps to the single resident Qwen3-Coder-30B
policy = {
    "version": "1",
    "model_name": "user.cohezion-router",
    "recipe": "collection.router",
    "components": [
        "Qwen3-Coder-30B-A3B-Instruct-GGUF"
    ],
    "routing": {
        "candidates": [
            "Qwen3-Coder-30B-A3B-Instruct-GGUF"
        ],
        "default_model": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
        "rules": [
            {
                "id": "direct-resident-all",
                "match": {"min_chars": 0},
                "route_to": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
                "outputs": {"reason": "single resident fast model"}
            }
        ]
    }
}

req = urllib.request.Request(url_pull, headers={"Content-Type": "application/json"}, data=json.dumps(policy).encode())
with urllib.request.urlopen(req, timeout=10) as resp:
    print("Policy Registered:", resp.read().decode())

time.sleep(1)

# Now test the query directly
url_chat = "http://127.0.0.1:13305/v1/chat/completions"
payload = {
    "model": "user.cohezion-router",
    "messages": [{"role": "user", "content": "What is 1 + 1?"}],
    "max_tokens": 10
}
req2 = urllib.request.Request(url_chat, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
t0 = time.perf_counter()
with urllib.request.urlopen(req2, timeout=10) as resp2:
    data = json.loads(resp2.read().decode())
    print(f"✓ PROVEN RESPONSE in {time.perf_counter() - t0:.2f}s: {data['choices'][0]['message']['content']}")
