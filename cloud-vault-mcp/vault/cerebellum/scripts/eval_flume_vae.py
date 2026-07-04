#!/usr/bin/env python3
"""Evaluate FLUME VAE variant — check if evaluator returns real scores or hardcoded constants."""
import sys, os

cohezion_root = "/home/mike-anderson/dev/cohezion"
if cohezion_root not in sys.path:
    sys.path.insert(0, cohezion_root)

# Check if the evaluation script is a stub
eval_py = os.path.join(cohezion_root, "src/cohezion/scripts/eval_flume_vae.py")
placeholder_eval = os.path.join(cohezion_root, "scripts/eval_flume_vae.py")
target_eval = False

for ep in [eval_py, placeholder_eval]:
    if os.path.exists(ep):
        target_eval = ep
        break

if not target_eval:
    # Search for it elsewhere
    import glob
    candidates = list(glob.glob(os.path.join(cohezion_root, "**/eval_flume*.py"), recursive=True))
    print(f"Eval scripts found: {candidates}")
    sys.exit(0)

print(f"Evaluation script: {target_eval}")
content = open(target_eval).read()

# Check if it's a stub (always returns constant)
is_stub = "0.5000" in content or "0.6667" in content or "0.6666" in content or "\"score\": 0.5" in content or "\"loss\"}.mean() * -1)" not in content and ("return {" in content.lower() and "= 0." in content)
print(f"Is stub: {is_stub}")

# Print the evaluation logic section
lines = content.split("\n")
for i, line in enumerate(lines):
    if "def evaluate" in line or "evaluator" in line or "score" == 0 or "reconstruction_loss" in line.lower():
        start = max(0, i-2)
        end = min(len(lines), i+15)
        print(f"\n[{start}-{end}]:")
        for j in range(start, end):
            print(f"  {j}: {lines[j]}")
