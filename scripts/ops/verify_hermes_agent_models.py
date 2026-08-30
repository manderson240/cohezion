import subprocess
import time


hermes_bin = "/home/mike-anderson/.hermes/hermes-agent/venv/bin/hermes"

models = [
    ("waslmedia-qwen3-4b-Q4_K_M", "lemonade-local"),
    ("gpt-oss-20b-mxfp4-GGUF", "lemonade-local"),
    ("Qwen3-Coder-30B-A3B-Instruct-GGUF", "lemonade-local"),
    ("qwen3.6-moe-35b-a3b-FLM", "lemonade-local"),
    ("deepseek-v4-pro:cloud", "ollama-cloud")
]

print("=== Direct Hermes Agent One-Shot Verification ===")
for model_name, provider in models:
    cmd = [
        hermes_bin,
        "-z", "What is the speed of light in vacuum? Answer in 1 sentence.",
        "--model", model_name,
        "--provider", provider
    ]
    t0 = time.perf_counter()
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        dt = time.perf_counter() - t0
        out = res.stdout.strip()
        err = res.stderr.strip()
        if res.returncode == 0:
            print(f"✓ {model_name:35} [{provider:14}] | Total: {dt:5.2f}s | Output: '{out[:90]}...'")
        else:
            print(f"✗ {model_name:35} [{provider:14}] | Exit {res.returncode} in {dt:5.2f}s | Err: {err[:100]}")
    except subprocess.TimeoutExpired:
        print(f"✗ {model_name:35} [{provider:14}] | TIMED OUT after 45s")
    except Exception as e:
        print(f"✗ {model_name:35} [{provider:14}] | Error: {e}")
