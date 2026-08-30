# ⚖️ Decision Matrix: 1 Large Monolithic Model (70B-128B) vs Heterogeneous Swarm

**Hardware Platform**: AMD Strix Halo (128GB Unified Memory, 210 GB/s bandwidth)  
**Date**: 2026-08-24  

| Workload / Domain | Single Large Model (70B-128B) | Heterogeneous SLM Swarm (8B-35B) | Optimal Strategy |
| :--- | :--- | :--- | :--- |
| 1. Deep Cross-File Architectural Refactoring & Global Invariant Synthesis | 👑 SUPERIOR: A 70B/72B model holds the entire 128k multi-file repo structure in unified attention without coordination loss or telephone-game drift. | ❌ WEAK: Swarms must pass summaries between agents via EventBus, risking loss of subtle cross-module type invariants and global state bugs. | **Single Large Model** |
| 2. High-Degree Mathematical Proofs & Formal Logic (AIMO / Sheaf Cohomology) | 👑 SUPERIOR: Deep reasoning density (e.g. DeepSeek-R1-70B) can formulate complex algebraic topology and non-local proofs that smaller 8B/20B models fragment. | ❌ WEAK: Decomposing a monolithic mathematical proof into sub-agent pieces often breaks the deductive chain. | **Single Large Model** |
| 3. High-Throughput Parallel Competition Simulations & Rollouts | ❌ SLOW: Sequential single-thread bottleneck. Running 5,000 Pokemon TCG matches or 1,000 ARC tasks takes hours. | 👑 SUPERIOR: Spawns 16 parallel workers across NPU, iGPU, and CPU threads (22,700+ games/sec in 0.22s, 10.39s across 1000 ARC tasks). | **Heterogeneous Swarm** |
| 4. Multi-Perspective Adversarial Audits & Red-Teaming | ❌ BIASED: A single model has single-model bias and struggles to genuinely attack its own assumptions in a single prompt context. | 👑 SUPERIOR: Genuinely independent personas (Cynical Grandmaster vs Sandbox Security Lead vs Kernel Architect) critique code from orthogonal angles. | **Heterogeneous Swarm** |
| 5. Memory Bus Saturation & Thermal Efficiency | ⚠️ HEAVY: 45GB weight sweeps at 210 GB/s draw ~90-110W sustained power on Strix Halo. | 👑 EFFICIENT: Small active weights (8B/3B on NPU at ~15W) leave memory bus free for background ZFS, compiler, and AST verification. | **Heterogeneous Swarm** |
