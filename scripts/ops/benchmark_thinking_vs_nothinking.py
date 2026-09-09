import json
import time
import urllib.request


url = "http://127.0.0.1:13305/v1/chat/completions"

# 1. Standard prompt (Model thinks by default)
payload_default = {
    "model": "waslmedia-qwen3-4b-Q4_K_M",
    "messages": [
        {"role": "user", "content": "What is 25 * 4?"}
    ],
    "max_tokens": 50,
    "stream": True
}

# 2. Prompt with explicit instruction to skip thinking / reasoning tags
payload_fast = {
    "model": "waslmedia-qwen3-4b-Q4_K_M",
    "messages": [
        {"role": "system", "content": "You are a direct calculator. Output ONLY the raw answer without any internal thinking or explanation."},
        {"role": "user", "content": "What is 25 * 4?"}
    ],
    "max_tokens": 50,
    "stream": True
}

def run_test(name, p):
    print(f"\n--- Running {name} ---")
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(p).encode())
    t0 = time.perf_counter()
    first_token = None
    reasoning_text = ""
    content_text = ""
    with urllib.request.urlopen(req, timeout=15) as resp:
        for line in resp:
            l = line.decode('utf-8').strip()
            if l.startswith("data: ") and l != "data: [DONE]":
                d = json.loads(l[6:])
                delta = d["choices"][0]["delta"]
                r = delta.get("reasoning_content") or ""
                c = delta.get("content") or ""
                if r or c:
                    if first_token is None:
                        first_token = time.perf_counter() - t0
                    reasoning_text += r
                    content_text += c
    dt = time.perf_counter() - t0
    print(f"TTFT: {first_token:.2f}s | Total: {dt:.2f}s")
    if reasoning_text:
        print(f"Thinking Tokens ({len(reasoning_text.split())} words): '{reasoning_text[:120]}...'")
    print(f"Final Answer: '{content_text.strip()}'")

run_test("Default Turn", payload_default)
run_test("Direct (No-Thinking) Turn", payload_fast)
