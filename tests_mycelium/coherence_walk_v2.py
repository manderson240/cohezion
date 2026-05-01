
import json
import math
import random


TARGET = 0.5
STEP_SIZE = 0.02
SEED = 42
random.seed(SEED)
coherence = 0.5
trajectory = [coherence]
for _ in range(200):
    drift = (TARGET - coherence) * 0.1
    noise = random.gauss(0, STEP_SIZE)
    coherence = coherence + drift + noise
    if coherence > 1.0:
        coherence = 1.0 - (coherence - 1.0)
    elif coherence < 0.0:
        coherence = 0.0 + (0.0 - coherence)
    coherence = max(0.0, min(1.0, coherence))
    trajectory.append(round(coherence, 6))
mean_c = sum(trajectory) / len(trajectory)
std_c = math.sqrt(sum((c-mean_c)**2 for c in trajectory) / len(trajectory))
result = {
    "target": TARGET,
    "mean": round(mean_c, 6),
    "std": round(std_c, 6),
    "final": trajectory[-1],
    "min": min(trajectory),
    "max": max(trajectory),
}
print(json.dumps(result, indent=2))
