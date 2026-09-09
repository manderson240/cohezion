import json
import urllib.request


# Let's query what router is returning for a simple prompt
url = "http://127.0.0.1:13305/v1/chat/completions"
payload = {
    "model": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "messages": [{"role": "user", "content": "Say hello."}],
    "max_tokens": 10
}

req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        print("Direct Qwen3-Coder-30B Response:", data["choices"][0]["message"]["content"])
except Exception as e:
    print("Direct Qwen3-Coder-30B Error:", e)
