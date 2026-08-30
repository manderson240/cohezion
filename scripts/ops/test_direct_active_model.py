#!/usr/bin/env python3
"""Direct test against currently resident active Lemonade model with reasoning content extraction."""

import json
import time
import urllib.request


url = "http://127.0.0.1:13305/v1/chat/completions"

payload = {
    "model": "Qwen3.6-35B-A3B-MTP-GGUF",
    "messages": [
        {"role": "user", "content": "Explain what you are doing in 2 short bullet points."}
    ],
    "max_tokens": 50,
    "stream": True
}

req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
t0 = time.perf_counter()
ttft = None
tokens = 0

with urllib.request.urlopen(req, timeout=30) as resp:
    for line in resp:
        l = line.decode('utf-8').strip()
        if l.startswith("data: ") and l != "data: [DONE]":
            try:
                d = json.loads(l[6:])
                delta = d["choices"][0]["delta"]
                c = delta.get("content") or delta.get("reasoning_content") or ""
                if c:
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                        print(f"⏱ Time to First Token (TTFT): {ttft:.2f}s")
                    print(c, end="", flush=True)
                    tokens += 1
            except Exception:
                pass

total_t = time.perf_counter() - t0
tps = tokens / (total_t - (ttft or 0)) if total_t > (ttft or 0) else 0
print(f"\n⏱ Total Time: {total_t:.2f}s | Decode: {tps:.1f} tok/s")
