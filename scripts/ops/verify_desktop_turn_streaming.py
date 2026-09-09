import subprocess
import time

hermes_bin = "/home/mike-anderson/.hermes/hermes-agent/venv/bin/hermes"

cmd = [
    hermes_bin,
    "-z", "How well can you perform time to first token? Respond in 1 sentence.",
    "-m", "user.cohezion-router",
    "--provider", "lemonade-local"
]

print("Running Hermes -z turn with user.cohezion-router...")
t0 = time.perf_counter()
res = subprocess.run(cmd, capture_output=True, text=True)
dt = time.perf_counter() - t0

print(f"Exit Code: {res.returncode} in {dt:.2f}s")
print(f"Stdout: {res.stdout.strip()}")
if res.stderr:
    print(f"Stderr: {res.stderr.strip()}")
