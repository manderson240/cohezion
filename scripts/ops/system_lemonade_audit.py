import json
import urllib.request


# Check models from master Lemonade router
req = urllib.request.Request("http://127.0.0.1:13305/v1/models")
with urllib.request.urlopen(req, timeout=5) as resp:
    data = json.loads(resp.read().decode())
    print("Lemonade Models Count:", len(data.get("data", [])))

# Let's test waslmedia-4b directly on Lemonade to verify it is responsive
payload = {
    "model": "waslmedia-qwen3-4b-Q4_K_M",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
}
req2 = urllib.request.Request("http://127.0.0.1:13305/v1/chat/completions", headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
try:
    with urllib.request.urlopen(req2, timeout=5) as resp2:
        d2 = json.loads(resp2.read().decode())
        print("waslmedia-4b response:", d2["choices"][0]["message"]["content"])
except Exception as e:
    print("waslmedia-4b error:", e)
