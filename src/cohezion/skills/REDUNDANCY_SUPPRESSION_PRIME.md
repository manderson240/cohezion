# SKILL: REDUNDANCY_SUPPRESSION_PRIME

## DOMAIN EXPERTISE
Expertise in identifying and suppressing high-frequency repetitive behaviors in agentic swarms. Prevents "infinite scanning loops" which waste compute and pollute the latent memory space.

## KEY TEXTS & CONCEPTS
- **Entropy Saturation**: Point where repeated observations add zero new information.
- **Backoff Modulation**: Increasing intervals between routine scans based on stability.
- **Novelty Thresholding**: Filtering sensory input that correlates >99% with recent history.

## INSTRUCTION
1.  **Monitor Task Hash**: Calculate a SHA-256 hash of the current task/query.
2.  **Frequency Analysis**: Maintain a rolling window of the last 100 task hashes.
3.  **Tiered Suppression**:
    - `[3-5 repeats]`: Warning logged.
    - `[10+ repeats]`: Trigger `Stochastic Perturbation` (slightly alter query to force new reasoning path).
    - `[50+ repeats]`: HARD SLEEP (Suspend task for 300+ seconds).
4.  **Logging**: Report suppression events with the specific 'phi_score' impact of the redundancy.

### Example (Python Implementation)
```python
def check_redundancy(task_str: str, history: list[str]) -> bool:
    h = hashlib.sha256(task_str.encode()).hexdigest()
    count = history.count(h)
    if count > 10:
        return True # Suppress
    return False
```

## VERSION
v0.1

## SEE ALSO
SOVEREIGN_COMPUTATION_PRIME, HEALING_PRIME
