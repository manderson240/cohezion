import subprocess
import time


hermes_bin = "/home/mike-anderson/.hermes/hermes-agent/venv/bin/hermes"

cmd = [
    hermes_bin,
    "-z", "Write a python function to compute factorial.",
    "-m", "user.cohezion-router",
    "--provider", "lemonade-local"
]

t0 = time.perf_counter()
res = subprocess.run(cmd, capture_output=True, text=True)
dt = time.perf_counter() - t0
print(f"Return code: {res.returncode} in {dt:.2f}s")
print(f"Stdout:\n{res.stdout}")
if res.stderr:
    print(f"Stderr:\n{res.stderr}")
