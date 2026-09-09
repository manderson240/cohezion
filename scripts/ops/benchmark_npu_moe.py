import json
import time
import urllib.request


# Let's test qwen3.6-moe-35b-a3b-FLM on NPU vs Qwen3.6-35B-A3B-MTP-GGUF
models_to_test = [
    "qwen3.6-moe-35b-a3b-FLM",
    "Qwen3.6-35B-A3B-MTP-GGUF",
    "Qwen3-Coder-30B-A3B-Instruct-GGUF"
]

for m in models_to_test:
    print(f"\nTesting {m}...")
    url = "http://127.0.0.1:13305/v1/chat/completions"
    payload = {
        "model": m,
        "messages": [
            {"role": "user", "content": "What is the capital of France?"}
        ],
        "max_tokens": 20,
        "stream": True
    }
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
    t0 = time.perf_counter()
    first_token = None
    tokens = 0
    reasoning_tokens = 0
    text = ""
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            for line in resp:
                l = line.decode('utf-8').strip()
                if l.startswith("data: ") and l != "data: [DONE]":
                    d = json.loads(l[6:])
                    delta = d["choices"][0]["delta"]
                    r = delta.get("reasoning_content") or ""
                    tok = delta.get("content") or ""
                    if r:
                        reasoning_tokens += 1
                        if first_token is None:
                            first_token = time.perf_counter() - t0
                    if tok:
                        tokens += 1
                        if first_token is None:
                            first_token = time.perf_counter() - t0
                        text += tok
        total_time = time.perf_counter() - t0
        tps = (tokens + reasoning_tokens) / (total_time - (first_token or 0)) if total_time > (first_token or 0) else 0
        print(f"✓ {m} Result:")
        print(f"   TTFT: {first_token:.2f}s | Speed: {tps:.1f} tok/s | Total: {total_time:.2f}s")
        print(f"   Thinking Tokens: {reasoning_tokens} | Answer Tokens: {tokens}")
        print(f"   Output: '{text.strip()}'")
    except Exception as e:
        print(f"✗ {m} Error: {e}")
