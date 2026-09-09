import json
import time
import urllib.request


url = "http://127.0.0.1:13305/v1/chat/completions"

payload = {
    "model": "waslmedia-qwen3-4b-Q4_K_M",
    "messages": [
        {"role": "user", "content": "Write a python function to calculate the nth Fibonacci number."}
    ],
    "max_tokens": 500,
    "stream": True
}

req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
t0 = time.perf_counter()
first_token = None
reasoning_tokens = 0
content_tokens = 0

with urllib.request.urlopen(req, timeout=30) as resp:
    for line in resp:
        l = line.decode('utf-8').strip()
        if l.startswith("data: ") and l != "data: [DONE]":
            d = json.loads(l[6:])
            delta = d["choices"][0]["delta"]
            r = delta.get("reasoning_content") or ""
            c = delta.get("content") or ""
            if r:
                if first_token is None:
                    first_token = time.perf_counter() - t0
                reasoning_tokens += 1
            if c:
                if first_token is None:
                    first_token = time.perf_counter() - t0
                content_tokens += 1

total_t = time.perf_counter() - t0
print(f"Time to First Token: {first_token:.2f}s")
print(f"Reasoning/Thinking Tokens: {reasoning_tokens} tokens")
print(f"Actual Answer Tokens: {content_tokens} tokens")
print(f"Total Time: {total_t:.2f}s (Decode Speed: {(reasoning_tokens + content_tokens)/(total_t - first_token):.1f} tok/s)")
