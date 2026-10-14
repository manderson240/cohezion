# Research Synthesis: Evo$^2$: Evolving the Evolver through Weight-Harness Co-Evolution (arXiv:2610.13025)

## 1. Executive Summary & Bibliographic Metadata
- **Title**: Evo$^2$: Evolving the Evolver through Weight-Harness Co-Evolution
- **arXiv ID**: `arXiv:2610.13025v1` [cs.AI, cs.LG, cs.SE]
- **Authors**: Chejian Xu, Shujian Zhang, Wenxuan Zhou, John Lambert, Beck Chen, Bo Li, Andrew Hard, Rajiv Mathews (UC Berkeley, UIUC, Google DeepMind)
- **Primary Breakthrough**: Bridges the historical divide between *weight optimization* (fixed evaluators, evolving model parameters) and *harness engineering* (fixed models, evolving scaffold prompts/verifiers). Evo$^2$ introduces a unified framework where the model simultaneously acts as both **Proposer** (modifying execution harnesses) and **Reflector** (diagnosing execution outcomes), navigating a structured **Harness Tree** via genetic crossover, trained end-to-end via **EvoTIDE** (Tree-guided Interleaved Dual-role Evolution).

---

## 2. Core Mathematical & Architectural Formalism

### 2.1 The Co-Evolutionary Optimization Problem
Traditional agentic systems solve:
$$\max_{\theta} \mathbb{E}_{\tau \sim \pi_\theta, h_0} [R(\tau, h_0)] \quad \text{or} \quad \max_{h \in \mathcal{H}} \mathbb{E}_{\tau \sim \pi_{\theta_0}, h} [R(\tau, h)]$$
Evo$^2$ formalizes the joint bi-level co-evolution:
$$\max_{\theta, h \in \mathcal{H}} \mathcal{J}(\theta, h) = \mathbb{E}_{\tau \sim \pi_\theta(h)} [R(\tau, h)] - \lambda \mathcal{D}_{\text{complexity}}(h)$$
where $\theta$ represents the shared policy parameters and $h$ represents the deterministic evaluation and execution harness.

### 2.2 Dual-Role Policy Formulation
A single policy $\pi_\theta$ alternates between two complementary functional roles:
1. **Proposer Role ($\pi_\theta^{\text{prop}}$)**:
   Given the current task $x$, harness state $h_t$, and diagnostic context $\delta_t$, generates a code modification / mutation $\Delta h$:
   $$\Delta h \sim \pi_\theta^{\text{prop}}(\cdot \mid x, h_t, \delta_t)$$
2. **Reflector Role ($\pi_\theta^{\text{refl}}$)**:
   Given the execution trajectory $\tau_t = (h_t(x), y_t, \mathcal{E}_t)$ where $\mathcal{E}_t$ contains stdout/stderr/test trace feedback, generates an actionable diagnostic reflection $\delta_{t+1}$:
   $$\delta_{t+1} \sim \pi_\theta^{\text{refl}}(\cdot \mid x, h_t, \tau_t, \mathcal{E}_t)$$

### 2.3 The Harness Tree ($\mathcal{T}$) & Crossover Search
Instead of linear revision chains, harness states are arranged as nodes in a tree $\mathcal{T} = (\mathcal{V}, \mathcal{E})$:
- **Node $v_i \in \mathcal{V}$**: Encapsulates harness code $h_i$, parent pointer $p(i)$, score vector $\mathbf{s}_i$, and execution trace $\mathcal{E}_i$.
- **Branch Crossover Operator**:
  Given two promising harness variants $h_A$ (e.g., strong ranking loss) and $h_B$ (e.g., robust boundary monotonicity projection), the Reflector extracts the high-performing invariant sub-modules $m_A \subset h_A$ and $m_B \subset h_B$. The Proposer synthesizes the child harness:
  $$h_{\text{child}} = \text{Crossover}(h_A, h_B; \delta_{A,B}) \sim \pi_\theta^{\text{prop}}(\cdot \mid h_A, h_B, \delta_{A,B})$$

### 2.4 EvoTIDE: Trajectory Recovery & Training Dynamics
When an execution trace contains syntax errors or partial exceptions:
1. **Edit Extraction & AST Parsing**: Parses candidate diffs into deterministic AST blocks, isolating syntax errors from semantic improvements.
2. **Prefix Continuation**: Recovers the trajectory by identifying the longest valid prefix state $h_{\text{prefix}}$ and prompting $\pi_\theta^{\text{refl}}$ to specifically diagnose the crash site.
3. **Interleaved Policy Optimization**:
   The policy is updated using a joint reward:
   $$R_{\text{total}} = R_{\text{prop}}(\Delta h) + \alpha R_{\text{refl}}(\delta)$$
   where $R_{\text{refl}}$ rewards diagnosis fidelity (correctly identifying error line and root cause) and $R_{\text{prop}}$ rewards harness performance gains ($s(h') > s(h)$).

---

## 3. Cohezion Integration Architecture

In Cohezion, Evo$^2$ provides the foundational engine for **continuous recursive self-improvement ("Cohezion improving Cohezion")**:
1. **Unified Module**: `src/cohezion/compound/evo2_coevolution.py`
   - `DualRolePolicy`: Wraps Ollama Cloud models (`glm-5.3:cloud`, `deepseek-v4-pro:cloud`) and local models for dual Proposer/Reflector dispatch.
   - `HarnessTree`: DAG tracking harness variants, parent lineage, metrics, and AST verification states.
   - `EvoTIDEEngine`: Trajectory repair, error localization, prefix continuation, and crossover synthesis.
2. **PRIME Skill**: `src/cohezion/skills/EVO2_WEIGHT_HARNESS_COEVOLUTION_PRIME.md`
3. **Kaggle Application**: Continuous automatic discovery of optimal feature engineering, loss blending weights, and post-processing calibration across RSNA Knee, ARC Prize, and CASMI26.
