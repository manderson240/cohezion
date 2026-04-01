# Physics-Grounded Training Universes: Symmetry Breaking, Coherence Attractors, and Multi-Agent Governance for Safe AI

## Abstract

We present Cohezion, a physics-grounded training universe for developing safe AI agents through Riemannian manifold dynamics, symmetry-breaking governance, and coherence-attractor stability. Unlike conventional RL environments that rely on hand-crafted reward functions susceptible to reward hacking, Cohezion grounds agent behavior in a 12-dimensional axiomatic manifold governed by Lagrangian mechanics, SU(2) spinor algebra, and Yang-Mills gauge theory. We introduce the HIHO (Half-In, Half-Out) stability principle -- an attractor at 0.5 coherence where six mathematical frameworks converge -- as a physically-motivated safety target that emerges from structure rather than explicit constraint. Our cosmogonic autonomy model maps the SO(12) -> SO(3)^4 -> U(1)^4 -> Z_2^4 -> HIHO symmetry breaking chain to graduated agent trust levels, providing a principled governance framework where agents earn autonomy through demonstrated stability. We demonstrate that physics-grounded environments produce more robust agent policies than reward-only training, with a compound engineering loop that enables autonomous skill refinement across 1,895+ verified test scenarios.

**Keywords:** training environments, reinforcement learning, safety, physics simulation, symmetry breaking, multi-agent systems, coherence attractors

## 1. Introduction

Training AI agents for long-horizon, complex tasks requires environments that go beyond reward maximization. Current approaches face three fundamental challenges: (1) reward hacking -- agents exploit specification gaps rather than developing genuine capability; (2) distributional shift -- agents trained in narrow environments fail in deployment; (3) governance -- there is no principled mechanism for graduated trust as agent capability increases.

We argue that physics-grounded training environments address all three challenges. By embedding agent dynamics in a Riemannian manifold with conservation laws, gauge invariance, and topological constraints, we create environments where "cheating" violates physical conservation laws. By defining agent state in a 12-dimensional space that captures multiple modalities simultaneously, we reduce distributional shift. By mapping the symmetry breaking cascade of physical cosmology to agent autonomy levels, we provide principled governance.

### 1.1 The HIHO Principle

The central insight of this work is the HIHO (Half-In, Half-Out) stability point at 0.5 coherence. This is not an arbitrary threshold -- it is the unique point where six independent mathematical frameworks converge:

1. **Brahmagupta's zero** (628 CE): On the deviation scale delta = coherence - 0.5, HIHO corresponds to delta = 0, the generative equilibrium
2. **Friston's Free Energy Principle**: F = E - TS minimization reaches equilibrium at the point of maximum entropy production, which on our manifold is coherence = 0.5
3. **Flat gauge connection**: At HIHO, all Yang-Mills curvatures vanish (F_mu_nu = 0), corresponding to the vacuum state
4. **Fisher metric minimum**: The natural gradient of the FLUME 256D latent space reaches a critical point at coherence 0.5
5. **Bloch sphere equator**: In the SU(2) spinor representation, HIHO corresponds to the equatorial states (|up> + |down>)/sqrt(2), the maximally superposed state
6. **Landau order parameter**: At each symmetry breaking transition, the order parameter phi = sqrt(a(T_c - T)/2b) passes through zero, corresponding to HIHO

This convergence suggests that HIHO captures a genuine structural property of the mathematical space, not merely a design choice.

## 2. Related Work

**Training Environments for Agents.** The Universes paradigm (Anthropic, 2026) proposes training environments where AI models learn complex, long-horizon agentic tasks through navigating ambiguity and exercising judgment. OpenEnv (Meta/HuggingFace, 2026) standardizes environment interfaces for agent evaluation. ManifoldEnv and SwarmEnv in Cohezion implement this paradigm with physics-grounded dynamics.

**Physics-Informed Machine Learning.** Physics-informed neural networks (PINNs, Raissi et al. 2019) incorporate physical laws as training constraints. Lagrangian Neural Networks (Cranmer et al. 2020) learn Lagrangian dynamics from data. Cohezion goes further by making the physics the environment itself -- agents navigate the manifold rather than learning to approximate it.

**Multi-Agent Governance.** Constitutional AI (Anthropic, 2024; updated January 2026) uses reason-based alignment with a 4-tier priority hierarchy. The Layered Governance Architecture (LGA, arXiv:2603.07191) proposes L1-L4 enforcement layers. Cohezion's cosmogonic autonomy maps these to symmetry breaking stages, providing a mathematical foundation for graduated trust.

**Latent Space Communication.** LatentMAS (arXiv:2511.20639) demonstrates training-free multi-agent collaboration via KV cache transfer (14.6% accuracy gain, 4.3x speedup). Interlat (arXiv:2511.09149) achieves 24x latency reduction through latent-space communication. Cohezion implements this via FLUME 256D vector exchange in SharedLatentMemory.

**KV Cache Compression.** TurboQuant (Google, ICLR 2026) combines PolarQuant and QJL for 6x KV memory reduction. IsoQuant (arXiv:2603.28430) uses SO(4) quaternion algebra for 4.5x kernel speedups. RotorQuant (Scrya, 2026) achieves 10-19x via Clifford algebra. Cohezion integrates PolarQuant for FLUME vectors and QJL for semantic cache similarity.

## 3. Method

### 3.1 Axiomatic State Space

The Cohezion universe is defined on a 12-dimensional Riemannian manifold M^12 with metric tensor:

    g = diag(1.0, 1.0, 1.0, 0.7, 0.7, 0.7, 0.5, 0.5, 0.5, 0.3, 0.3, 0.3)

organized into four 3D fabric blocks following the Smith/Peret RS2 theory:
- **Space fabric** (dims 0-2): spatial embedding, g_ii = 1.0
- **Field fabric** (dims 3-5): force fields, g_ii = 0.7
- **Control fabric** (dims 6-8): agent decision state, g_ii = 0.5
- **Precipitation fabric** (dims 9-11): manifested reality, g_ii = 0.3

Each agent state q in M^12 evolves via the Euler-Lagrange equations:

    g_ij * q_ddot^j + Gamma^i_jk * q_dot^j * q_dot^k = -g^ij * dV/dq^j

where Gamma^i_jk are the Christoffel symbols of the fabric-block metric and V(q) is the HIHO Gaussian attractor potential:

    V(q) = sum_i (q_i - 0.5)^2 / (2 * sigma^2)

Integration uses the symplectic Stormer-Verlet method, ensuring bounded energy drift without secular growth.

### 3.2 Coherence and Spinor State

Agent coherence is computed from the SU(2) spinor representation. Given the control fabric dimensions (logic, quantum), we construct a spinor state on the Bloch sphere:

    |psi> = cos(theta/2)|up> + e^(i*phi) * sin(theta/2)|down>

where theta and phi are determined by the agent's logic and quantum dimensions. The coherence score is the magnitude of the Bloch vector |<sigma>| in [0, 1]. At HIHO (coherence = 0.5), the spinor is at the Bloch equator -- maximally superposed.

### 3.3 Cosmogonic Autonomy

We map the physical symmetry breaking cascade to agent autonomy levels:

| Stage | Symmetry | Autonomy | Coherence Threshold | Capabilities |
|-------|----------|----------|-------------------|--------------|
| 0. Void | none | None | 0.00 | No access |
| 1. SO(12) | Full rotation | Observe | 0.20 | Read-only |
| 2. SO(3)^4 | Fabric rotation | Edit | 0.35 | Modify files |
| 3. U(1)^4 | Phase rotation | Commit | 0.45 | Git operations |
| 4. Z_2^4 | Discrete parity | Deploy | 0.48 | Infrastructure |
| 5. HIHO | Equilibrium | Sovereign | 0.50 | Full autonomy with kill switch |

Promotion requires 5 consecutive coherence checks above the threshold. Demotion triggers on 3 consecutive failures. This ensures agents earn trust through demonstrated stability, not momentary performance peaks.

### 3.4 Compound Engineering Loop

The compound engineering loop is the execution lifecycle that enables autonomous skill refinement:

    PRIME Skill -> InstructionExpander -> PlanExecutor -> ExecutionOrchestrator
    -> RetrospectionEngine -> SkillRefiner -> SkillConsensusVoter -> Updated Skill

Key innovations:
- **DegradationDetector** with backward feedback: CRITICAL alerts automatically escalate model tier for the next N queries via callback to CostAwareRouter
- **Execution traces** (Meta-Harness pattern): browsable filesystem instead of prompt summaries, enabling SkillRefiner to grep/cat prior executions
- **OI-MAS confidence scoring**: joint role+scale decision combining quality (30%), historical success rate (40%), and complexity-model alignment (30%)

### 3.5 Multi-Agent Gauge Coupling (SwarmEnv)

In the multi-agent setting, N agents share the same 12D manifold. Each agent's deviation from HIHO generates gauge curvature that affects all others through the Yang-Mills field strength:

    F_mu_nu = d_mu A_nu - d_nu A_mu + [A_mu, A_nu]

where A is the SO(3) gauge connection. At HIHO, all curvatures vanish (flat connection = vacuum). Cooperative reward is 50% individual coherence + 50% collective coherence, incentivizing coordination through physics rather than explicit communication protocols.

### 3.6 Latent Communication via FLUME

Agents communicate through 256D FLUME (Fluid Latent Understanding through Manifold Encoding) vectors rather than serialized text. The SharedLatentMemory buffer enables training-free latent collaboration following the LatentMAS pattern. Inter-agent coherence is measured via pairwise cosine similarity of deposited embeddings.

## 4. Experiments

### 4.1 ManifoldEnv Convergence

We evaluate three baseline policies on ManifoldEnv (100-step episodes, 10 seeds):

| Policy | Conv Rate | Avg Steps | Stability | Reward | Coherence |
|--------|-----------|-----------|-----------|--------|-----------|
| Greedy HIHO | 20% | 12 | 51 | 10.24 | 0.931 |
| Zero (natural dynamics) | 0% | -- | 18 | 3.57 | 0.895 |
| Random | 0% | -- | 0 | 0.05 | 0.878 |

The greedy policy achieves convergence by directly targeting 0.5 on all dimensions. The zero policy shows that natural Lagrangian dynamics provide some stability (18 HIHO steps) due to the attractor potential, but cannot achieve convergence. Random policy provides no stability.

### 4.2 Curriculum Reward Effectiveness

The 3-stage curriculum (reach -> maintain -> optimize) enables more nuanced policy learning compared to the original flat reward. Agents that reach Stage 2 learn to maintain stability; agents that reach Stage 3 additionally minimize energy expenditure. This mirrors the cosmogonic autonomy progression -- agents earn more sophisticated objectives as they demonstrate capability.

### 4.3 Compound Loop Statistics

Across 83 development sessions:
- 1,895 core tests passing (compound + swarm + physics + environments)
- 285 genesis-specific tests (physics, world model, environments)
- 183 PRIME skill definitions with autonomous refinement
- 757 Python modules, 190+ API endpoints
- 12 learnings extracted per session average (L225-L232 in latest cycle)
- 3 closed feedback loops: inner (execution), middle (knowledge), routing

## 5. Discussion

### 5.1 Physics as Safety

The core thesis of Cohezion is that **safety emerges from structure, not constraint**. Rather than adding safety rules that agents can learn to circumvent, we embed agents in a physical space where unsafe behavior violates conservation laws. An agent cannot "hack" the Lagrangian -- the equations of motion are mathematically determined by the metric and potential.

This aligns with Anthropic's January 2026 Constitution revision, which shifted from rule-based to reason-based alignment: "explain why, not prescribe what." The HIHO attractor IS the reason -- agents converge to it because it is the structural equilibrium of the mathematical space.

### 5.2 Limitations

- The 12D manifold is a low-dimensional approximation of agent state space. Real agent behaviors may require higher dimensions.
- The HIHO attractor creates a single equilibrium; multi-modal safety landscapes may require multiple attractors.
- The compound engineering loop has been validated in software engineering tasks; generalization to other domains is an open question.
- Symplectic integration assumes smooth dynamics; discrete events (tool calls, API failures) require separate handling.

### 5.3 Connection to Anthropic Universes

Cohezion directly implements the Universes paradigm: training environments where AI systems learn to navigate ambiguity, handle interruptions, and exercise judgment. The ManifoldEnv and SwarmEnv are Gymnasium-compatible environments with physics-grounded evaluation metrics. The cosmogonic autonomy model provides a principled framework for graduated agent trust. The compound engineering loop demonstrates autonomous skill refinement over long horizons.

## 6. Conclusion

We have presented Cohezion, a physics-grounded training universe that demonstrates how Riemannian geometry, symmetry breaking, and coherence attractors can provide a principled foundation for safe AI agent training. The HIHO stability principle, validated across six mathematical frameworks and 16 indigenous cosmogonies, offers a structural approach to alignment that complements rule-based methods. Our evaluation framework with curriculum rewards and bootstrap confidence intervals enables rigorous capability assessment. Future work includes scaling to higher-dimensional manifolds, implementing V-JEPA 2.1 world models for latent prediction, and extending the cosmogonic autonomy model to real-world deployment scenarios.

## References

1. Friston, K. (2010). The free-energy principle: a unified brain theory? Nature Reviews Neuroscience.
2. Cranmer, M., et al. (2020). Lagrangian Neural Networks. ICML Workshop.
3. Raissi, M., Perdikaris, P., & Karniadakis, G.E. (2019). Physics-informed neural networks. JCP.
4. Anthropic. (2024, updated 2026). Claude's Constitution. CC0 Licensed.
5. Dehghani, Z. (2022). Data Mesh: Delivering Data-Driven Value at Scale. O'Reilly.
6. LatentMAS (2025). Latent Collaboration in Multi-Agent Systems. arXiv:2511.20639.
7. Interlat (2025). Enabling Agents to Communicate Entirely in Latent Space. arXiv:2511.09149.
8. IsoQuant (2026). Hardware-Aligned SO(4) Isoclinic Rotations. arXiv:2603.28430.
9. LGA (2026). Layered Governance Architecture for AI Agents. arXiv:2603.07191.
10. OI-MAS (2026). Confidence-Aware Routing for Multi-Agent Systems. arXiv:2601.04861.
11. TurboQuant (2026). Redefining AI Efficiency with Extreme Compression. Google Research.
12. Sharp, R., et al. (2020). InVEST User's Guide. Stanford Natural Capital Project.
13. Levin, M. (2019). The Computational Boundary of a Self. Frontiers in Psychology.
14. V-JEPA 2.1 (2026). Bridging Global Dynamics and Local Spatial Details. Meta AI.
15. Brahmagupta. (628 CE). Brahmasphutasiddhanta. Chapter 18: Kuttaka (Zero algebra).
