import json
import time
import urllib.request


url = "http://127.0.0.1:13305/v1/chat/completions"
model = "Qwen3-Coder-30B-A3B-Instruct-GGUF"

payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello."}
    ],
    "stream": True,
    "max_tokens": 50
}

print(f"Connecting to {url} for model {model}...")
req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
t0 = time.perf_counter()

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("Connected! Reading stream...")
        count = 0
        for line in resp:
            l = line.decode('utf-8').strip()
            if l:
                print("RECV:", l)
                count += 1
                if count > 5:
                    break
        print(f"Success in {time.perf_counter() - t0:.2f}s")
except Exception as e:
    print(f"Error: {e}")
