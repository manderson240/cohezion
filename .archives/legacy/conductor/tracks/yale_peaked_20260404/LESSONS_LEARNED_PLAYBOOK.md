# Yale Peaked Hackathon 2026 - Lessons Learned Playbook

## Executive Summary
The Yale Peaked Hackathon 2026 challenge centered on "cracking" peaked circuits—quantum circuits designed to have a hidden high-probability bitstring. Our journey involved transitioning from a standard simulator approach to a sophisticated statistical "attack" strategy that bypassed hardware limits and billing restrictions.

## Key Strategies & Breakthroughs

### 1. The "Majority-Voting" Attack
- **Problem:** Low-bond-dimension MPS simulations (required for free-tier compatibility) were too noisy to produce a single "heavy" output.
- **Solution:** We implemented a bit-wise majority voting algorithm. Instead of looking for the most frequent *full* bitstring, we took the most frequent *bit* at each qubit position across all samples.
- **Result:** Successfully reconstructed the peak bitstring for P5-P8 even when individual samples had low fidelity.

### 2. Bootstrap Stability Analysis
- **Problem:** How to know if a majority-voted bitstring is actually the peak or just random noise?
- **Solution:** We used Bootstrap re-sampling (sampling with replacement) to create virtual batches of results. 
- **Metric:** We defined a "Stability" score based on how often the same peak emerged across bootstraps.
- **Impact:** Provided high confidence (60-100%) for P9 and P10 results without requiring paid GPU resources.

### 3. Topology-Aware Scaling
- **Insight:** Circuit connectivity (all-to-all vs. local) is the primary driver of MPS simulation difficulty.
- **Action:** We developed a topology analyzer using Qiskit to calculate average connectivity. This allowed us to predict the "cracking point" and adjust bond dimensions (e.g., increasing to 16 for P9/P10) strategically.

## Technical Stack
- **Simulator:** BlueQubit MPS (CPU/GPU)
- **Framework:** Qiskit (Circuit analysis and transpilation)
- **Language:** Python 3.11 (UV Managed)
- **Orchestration:** Cohezion Conductor (Task tracking and execution)

## Reflections & Future Improvements
- **Hybrid Local-Cloud:** Future challenges should start with a local "low-fidelity" sweep to calibrate the majority-voting logic before any cloud credits are spent.
- **Tree-based MPS:** For high-connectivity circuits like P9, transpiling to a tree structure before MPS simulation could further reduce the required bond dimension.
- **Automation:** The `submission_generator.py` and `BatchSolver` with SHA-256 caching proved essential for iterative refinement without data loss.

---
*Created on April 5, 2026, as part of the Cohezion Autonomous Challenge Execution.*
