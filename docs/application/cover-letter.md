# Cover Letter

**Mike Anderson**
Research Engineer, Universes

---

I have spent the past year building exactly what your Universes team builds: training environments for complex, long-horizon agentic tasks. The result is Cohezion, a 12-dimensional agentic universe engine with Gymnasium-compatible RL environments, physics-grounded dynamics, and a complete pipeline from environment trajectories to LLM training signals. This is not a prototype or a spec. It is 2,684 commits, 5,919 tests, and a research paper with 27 citations.

**Environments.** Cohezion implements three Gymnasium-registered RL environments on a 12D Riemannian manifold governed by Euler-Lagrange equations and Yang-Mills gauge theory. ManifoldEnv provides a 19D observation space and 12D continuous action space where agents navigate toward HIHO equilibrium (coherence at 0.5, equivalent to Friston's free energy minimum). SwarmEnv extends this to multi-agent settings with gauge field coupling, where one agent's motion generates curvature affecting all others. I built 5 task archetypes that directly target the capabilities your posting describes: HIHO Basin Navigation tests goal-directed behavior under Lagrangian dynamics; Interruption Recovery tests the ability to maintain context and recover coherence after mid-episode perturbation; Exotic Charge Tolerance tests robustness under adversarial noise. A JEPA world model (~86K params, causal masking) provides surprise-driven exploration, and persistent homology classifies agent trajectory topology for routing decisions. The sandbox system (Docker, systemd-run, and subprocess backends with per-sandbox divergence detection) provides the isolation infrastructure to run these environments safely.

**Evaluations.** I built a 6-axis CapabilityScorecard (Coherence Amplitude, Phase Locking, Exotic Charge Lifetime, Orbit Quality, TRIUNE Balance, Recovery Basin Radius) with bootstrap 95% confidence intervals, Mann-Whitney U tests, and Bonferroni correction. Each metric is derived from the physics of the environment rather than ad hoc proxies, meaning the evaluation measures what the environment is designed to teach. The compound engineering loop wraps evaluation into production: RequestAlignmentAnalyzer checks coherence and drift risk before execution, DegradationDetector monitors quality thresholds during execution, and RetrospectionEngine extracts learnings after execution. The LLM Training Bridge converts trajectories into RLHF rewards, DPO preference pairs, and judgment assessments, closing the loop from environment to model training.

**Debugging across research and production ML.** The Anthropic VLIW Challenge produced a 423x speedup (349 cycles, bit-exact) through systematic kernel optimization, not clever tricks. The BlueQubit Quantum Challenge required simulating 36 qubits via Matrix Product State decomposition (SNR 9,947 sigma). The Luma AMD Speedrun involves writing GEMM, MoE, and MLA kernels for the MI355X. Each of these required the same discipline: reproduce, instrument, hypothesize, test, verify. I applied the same systematic debugging methodology to the 5,919 tests in Cohezion, with singleton isolation patterns that prevent flaky tests from VAE state pollution, RL policy leakage, and logger coupling.

The codebase is at [github link] and the research paper is in `docs/papers/genesis-engine-paper.md`. I would welcome the opportunity to discuss how the Cohezion architecture maps to the problems the Universes team is solving and where my approach diverges from yours in productive ways.

Mike Anderson
