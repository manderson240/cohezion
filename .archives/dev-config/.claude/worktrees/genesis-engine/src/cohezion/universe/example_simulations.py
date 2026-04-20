"""Example simulation scripts for sandbox validation.

Provides complete Python scripts (as string constants) that can be injected
into any isolation backend. These serve as both test fixtures and
demonstration scripts for the sandbox pipeline.
"""

from __future__ import annotations


# Minimal validation script: prints system info and writes a result file
HELLO_SANDBOX = '''\
"""Hello Sandbox — minimal validation script."""
import json
import os
import platform
import sys
from pathlib import Path

output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

result = {
    "status": "ok",
    "python_version": platform.python_version(),
    "platform": platform.system(),
    "cwd": os.getcwd(),
    "pid": os.getpid(),
    "argv": sys.argv,
}

print(json.dumps(result, indent=2))

(output_dir / "result.json").write_text(json.dumps(result, indent=2))
'''

# Random walk tracking HIHO coherence toward the 0.5 target
COHERENCE_WALK = '''\
"""Coherence Walk — random walk tracking HIHO stability."""
import json
import math
import random
import sys
from pathlib import Path

STEPS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
TARGET = 0.5
STEP_SIZE = 0.02
SEED = 42

random.seed(SEED)

coherence = 0.5
trajectory = [coherence]

for _ in range(STEPS):
    # Mean-reverting random walk toward TARGET
    drift = (TARGET - coherence) * 0.1
    noise = random.gauss(0, STEP_SIZE)
    coherence = max(0.0, min(1.0, coherence + drift + noise))
    trajectory.append(round(coherence, 6))

mean_coherence = sum(trajectory) / len(trajectory)
std_coherence = math.sqrt(
    sum((c - mean_coherence) ** 2 for c in trajectory) / len(trajectory)
)

result = {
    "status": "ok",
    "steps": STEPS,
    "target": TARGET,
    "final_coherence": trajectory[-1],
    "mean_coherence": round(mean_coherence, 6),
    "std_coherence": round(std_coherence, 6),
    "min_coherence": min(trajectory),
    "max_coherence": max(trajectory),
}

print(json.dumps(result, indent=2))

output_dir = Path("output")
output_dir.mkdir(exist_ok=True)
(output_dir / "result.json").write_text(json.dumps(result, indent=2))
(output_dir / "trajectory.json").write_text(json.dumps(trajectory))
'''

EXAMPLES: dict[str, str] = {
    "hello": HELLO_SANDBOX,
    "coherence_walk": COHERENCE_WALK,
}
