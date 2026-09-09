import json
import time
import urllib.request


local_candidates = [
    ("waslmedia-qwen3-4b-Q4_K_M", 16384),
    ("DeepSeek-Qwen3-8B-GGUF", 32768),
    ("gemma-4-E4B-it-GGUF", 16384),
    ("gpt-oss-20b-mxfp4-GGUF", 32768),
    ("Qwen3-Coder-30B-A3B-Instruct-GGUF", 32768),
    ("Qwen3.6-35B-A3B-MTP-GGUF", 32768),
]

print("=== Local Silicon Latency & Throughput Benchmark ===")
for model_name, ctx in local_candidates:
    url = "http://127.0.0.1:13305/v1/chat/completions"
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a concise AI assistant."},
            {"role": "user", "content": "Explain gravity in exactly one sentence."}
        ],
        "max_tokens": 40,
        "stream": True
    }
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
    t0 = time.perf_counter()
    first_token = None
    tokens = 0
    text = ""
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            for line in resp:
                l = line.decode('utf-8').strip()
                if l.startswith("data: ") and l != "data: [DONE]":
                    d = json.loads(l[6:])
                    delta = d["choices"][0]["delta"]
                    tok = delta.get("content") or delta.get("reasoning_content") or ""
                    if tok:
                        if first_token is None:
                            first_token = time.perf_counter() - t0
                        tokens += 1
                        text += tok
        total_time = time.perf_counter() - t0
        tps = tokens / (total_time - (first_token or 0)) if total_time > (first_token or 0) else 0
        print(f"✓ {model_name:35} | TTFT: {first_token:.2f}s | Decode: {tps:5.1f} tok/s | Total: {total_time:.2f}s")
    except Exception as e:
        print(f"✗ {model_name:35} | FAILED ({e})")
