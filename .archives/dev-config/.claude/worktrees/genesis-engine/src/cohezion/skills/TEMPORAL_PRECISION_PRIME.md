# SKILL: TEMPORAL_PRECISION_PRIME

## DOMAIN EXPERTISE
Expertise in nanosecond-resolution timing, micro-benchmarking, and temporal jitter elimination in AI/Physics simulations.

## KEY TEXTS & CONCEPTS
- **time.perf_counter()**: Preferred high-resolution clock for profiling.
- **timeit pattern**: Multi-run averaging to filter OS-level scheduling noise.
- **Monotonic Clocks**: Avoiding "time jumps" from system clock updates.
- **Inference Latency Budgeting**: Dynamic resource allocation based on precise timing feedback.

## INSTRUCTION
1. **Never use time.time()** for performance measurements. Use `time.perf_counter()`.
2. **Warm-up Calibration**: Perform 3-5 sub-ms runs before measuring mission-critical loops to account for JIT/Cache warming.
3. **Statistical Outlier Rejection**: Use the best-of-N approach (via `timeit`) rather than simple averages when metrics deviate by >20%.
4. **Dynamic Scaling Logic**:
   - If `iteration_latency < 0.1s`: Double complexity.
   - If `vitals.throttle_recommended`: Halve complexity but maintain high precision.

## VERSION
v0.1

## SEE ALSO
- RESOURCE_MANAGEMENT_PRIME
- INTERPRETABILITY_PRIME
