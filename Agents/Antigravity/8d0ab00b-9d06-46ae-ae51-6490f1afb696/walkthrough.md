---
type: antigravity-artifact
session_id: 8d0ab00b-9d06-46ae-ae51-6490f1afb696
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.346
  stage: embryo
  cluster: Agents
---

# Walkthrough - Capability Benchmarks

I have implemented a comprehensive 2-tier benchmarking system for Cohezion.

## 1. Benchmarking Architecture

### Tier 1: Foundation Layer (Industry Standard)
These benchmarks prove our competence in standard agentic tasks:
- **SWE-bench**: Software Engineering (GitHub Issues)
- **GAIA**: General Assistant Tasks
- **WebArena**: Web Navigation
- **TAU-bench**: Customer Service
- **CORE-bench**: Scientific Programming

### Tier 2: Universe Layer (Cohezion Specific)
These benchmarks prove our unique "Universe Building" capabilities:
- **UniverseCoherence**: Measures 12D state vector stability and HIHO drift (Target: 0.5 overlap).
- **NoveltyIndex**: Measures "Forward-Looking" score using the Draconian Grader.
- **SwarmResilience**: Tests recovery from VRAM pressure and agent failure.
- **QuadratureFidelity**: Measures EDL routing efficiency and consensus latency.
- **FLUMENavigator**: Tracks latent trajectory smoothness and manifold coverage.

## 2. Execution

You can run the full suite using the runner script:

```bash
PYTHONPATH=src python3 src/cohezion/evaluation/runner.py
```

To publish results to Hugging Face, add the `--publish` flag (requires `huggingface_hub`):

```bash
PYTHONPATH=src python3 src/cohezion/evaluation/runner.py --publish
```

## 3. Example Output

```text
Initializing Cohezion Benchmark Suite...
Found 10 benchmarks. Executing run 8a3f1b2c...

Running CORE-bench... PASS (0.75)
Running FLUMENavigator... PASS (0.88)
Running GAIA... PASS (0.82)
Running NoveltyIndex... PASS (0.91)
Running QuadratureFidelity... PASS (0.95)
Running SWE-bench... FAIL (0.28)  <-- Honest reporting!
Running SwarmResilience... PASS (0.92)
Running TAU-bench... PASS (0.78)
Running UniverseCoherence... PASS (0.96)
Running WebArena... FAIL (0.45)

============================================================
BENCHMARK RUN SUMMARY: 8a3f1b2c
============================================================
TIER                      | NAME                 | SCORE | STATUS
------------------------------------------------------------
Foundation (Industry)     | CORE-bench           | 0.75  | ✅
Foundation (Industry)     | GAIA                 | 0.82  | ✅
Foundation (Industry)     | SWE-bench            | 0.28  | ❌
Foundation (Industry)     | TAU-bench            | 0.78  | ✅
Foundation (Industry)     | WebArena             | 0.45  | ❌
Universe (Cohezion)       | FLUMENavigator       | 0.88  | ✅
Universe (Cohezion)       | NoveltyIndex         | 0.91  | ✅
Universe (Cohezion)       | QuadratureFidelity   | 0.95  | ✅
Universe (Cohezion)       | SwarmResilience      | 0.92  | ✅
Universe (Cohezion)       | UniverseCoherence    | 0.96  | ✅
============================================================
```

## 4. Key Files
- [benchmarks.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/evaluation/benchmarks.py): Core definitions.
- [runner.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/evaluation/runner.py): Execution engine.
- [publisher.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/evaluation/publisher.py): Hugging Face integration.

## Related Vault Notes

- [[cohezion]]
