import json
import time
import urllib.request


url = "http://127.0.0.1:13305/v1/chat/completions"

# Simulate a turn with 57 messages of history (like the user's active session)
messages = [{"role": "system", "content": "You are Hermes Desktop."}]
for i in range(25):
    messages.append({"role": "user", "content": f"Turn {i}: Describe system architecture step {i}."})
    messages.append({"role": "assistant", "content": f"Step {i}: In step {i}, we execute hardware accelerated matrix multiplication."})

messages.append({"role": "user", "content": "Are we sure things are working as expected?"})

payload = {
    "model": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "messages": messages,
    "max_tokens": 40,
    "stream": True
}

print(f"Testing 50+ message history turn against {url}...")
req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
t0 = time.perf_counter()
first_token = None
text = ""

try:
    with urllib.request.urlopen(req, timeout=45) as resp:
        for line in resp:
            l = line.decode('utf-8').strip()
            if l.startswith("data: ") and l != "data: [DONE]":
                d = json.loads(l[6:])
                delta = d["choices"][0]["delta"]
                tok = delta.get("content") or delta.get("reasoning_content") or ""
                if tok:
                    if first_token is None:
                        first_token = time.perf_counter() - t0
                        print(f"⏱ Time to First Token (TTFT): {first_token:.2f}s")
                    text += tok
    print(f"✓ Total: {time.perf_counter() - t0:.2f}s | Output: '{text.strip()}'")
except Exception as e:
    print(f"✗ Failed: {e}")
