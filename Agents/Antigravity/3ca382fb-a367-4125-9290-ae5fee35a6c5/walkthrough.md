---
type: antigravity-artifact
session_id: 3ca382fb-a367-4125-9290-ae5fee35a6c5
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.64
  stage: embryo
  synapse_in: 0
  synapse_out: 1
---

# Walkthrough: The VLIW "Sub 400" Breakthrough (349 Cycles)

We achieved the record **349-cycle run** (a 423x speedup over the 148,000 baseline) through a combination of extreme instruction-level parallelism and hardware-specific engine balancing.

## The "Secret Sauce"

The primary driver of the sub-400 performance was **28-way window parallelism** via software pipelining. By processing 32 vectors (256 items) concurrently without explicit barriers, we allowed the simulator's scheduler to overlap loads and ALU operations from different "windows" of thought.

### Key Optimization Pillars:

1.  **Engine Balancing (Hash Hybrid & SG Offload)**: 
    - The `Hash Hybrid` optimization matches the specific linear pattern `a + (a << n) + b` and collapses it into a single `multiply_add` VALU instruction.
    - We offloaded scalar address additions to idle **ALU slots** (utilizing all 12 slots) to keep the 6 **VALU slots** free for the heavy lifting of the hash kernels.

2.  **Crown Cache (Level 1-2 Pre-broadcasting)**:
    - Instead of loading the tree root and top levels for every vector, we pre-broadcasted levels 0, 1, and 2 into permanent vector registers. This saved 1 VALU and 1 LOAD instruction per window per round.

3.  **Quadrature Nexus Scheduling**:
    - A 4-pass custom scheduler (forward, reverse, and tail compaction) pulled operations into the earliest possible bundles, ensuring the "tail" of the execution didn't drag out the cycle count.

4.  **Dead Write Elimination**:
    - We realized that in the final "wrap" round, the index update is never consumed. By skipping that `vstore`, we saved several high-latency cycles at the end of the run.

## Why "Another Platform" Fails (Hypothesis)

The record is highly dependent on the **Hardware Simulator Specs** (`problem.py`):
- **ALU Slots (12)**: This is an unusually large number of ALU slots for a VLIW architecture. Most standard VLIW simulators (and real hardware) have 4 or 8. Our scheduler aggressively fills these 12 slots to perform address math.
- **VLEN (8)**: The packing is optimized for 8-element SIMD. If the other platform uses a different VLEN (e.g. 4 or 16), the instruction packing will be suboptimal.
- **Non-blocking Loads**: Our simulator allows issued loads to be used in the very next cycle's ALU operations. If the other platform has a load-latency > 1, the pipeline stalls.

### References:
- [optimizer.py](file:///home/mike-anderson/dev/cohezion/research/challenges/anthropic_challenge/optimizer.py#L407) (The `build_kernel` implementation)
- [KEY_LEARNINGS.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/KEY_LEARNINGS.md#L3) (Learning 5 Summary)
- [SUBMISSION_README.md](file:///home/mike-anderson/dev/cohezion/research/challenges/anthropic_challenge/SUBMISSION_README.md) (Performance stats)

## Related Vault Notes

- [[cohezion]]
