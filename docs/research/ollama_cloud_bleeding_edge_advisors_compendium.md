# 🌐 Ollama Cloud Bleeding-Edge Advisors Compendium

**Date**: 2026-08-24  
**Frontier Models**: DeepSeek-V4 Pro (1.6T), Qwen-3.5 (397B), GLM-5.2 (Frontier Science)  

## DeepSeek-V4 Pro (1.6T Cloud): Sheaf Theory & Hyperbolic ARC Invariants
**Duration**: 59.66s

## Three Mathematical Formulations for ARC-AGI Program Synthesis

These formulations can be used separately or stacked: sheaf cohomology enforces local-to-global consistency, hyperbolic geodesic pruning controls search geometry, and MDL Bayesian search trees provide the global objective.

---

## 1. Sheaf Cohomology Restriction Maps Across Local Grid Neighborhoods

### Formulation

Let the ARC grid be a finite cell complex \(G=(V,E,C)\), where \(V\) are pixels or local patches, \(E\) are adjacency edges, and \(C\) are unit square cells.

Define a cellular sheaf \(\mathcal{F}\) on \(G\):

- Stalk \(\mathcal{F}(v)\) over each vertex \(v\): vector space of local program fragments or local transformation features.
- Stalk \(\mathcal{F}(e)\) over each edge \(e\): vector space of overlap/boundary features.
- Stalk \(\mathcal{F}(c)\) over each cell \(c\): cell-level constraint features.
- Restriction maps:
  \[
  \rho_{v,e}:\mathcal{F}(v)\to \mathcal{F}(e),\qquad \rho_{e,c}:\mathcal{F}(e)\to \mathcal{F}(c)
  \]

The sheaf cochain complex is

\[
0 \to C^0(G,\mathcal{F}) \xrightarrow{\delta^0} C^1(G,\mathcal{F}) \xrightarrow{\delta^1} C^2(G,\mathcal{F}) \to 0
\]

where

\[
C^0=\bigoplus_{v\in V}\mathcal{F}(v),\quad
C^1=\bigoplus_{e\in E}\mathcal{F}(e),\quad
C^2=\bigoplus_{c\in C}\mathcal{F}(c).
\]

For an oriented edge \(e=(v\to w)\),

\[
(\delta^0 s)(e)=\rho_{v,e}s_v-\rho_{w,e}s_w.
\]

For a cell \(c\) with boundary edges \(e\in \partial c\),

\[
(\delta^1 t)(c)=\sum_{e\in \partial c} [e:c]\,\rho_{e,c}t_e,
\]

where \([e:c]\in\{-1,+1\}\) is the orientation incidence.

The cohomology groups are

\[
H^0=\ker \delta^0,\qquad
H^1=\ker \delta^1 / \operatorname{im} \delta^0.
\]

A global program is a global section \(s\in C^0\) satisfying \(\delta^0 s=0\). If \(H^1\neq 0\), local program fragments cannot be glued into a global program without obstruction.

### Program synthesis objective

Let \(I\subseteq V\) be the set of vertices constrained by input-output examples. Define

\[
s^*=
\arg\min_{s\in C^0}
\left[
\sum_{e\in E}\|(\delta^0 s)(e)\|^2
+\lambda \sum_{v\in I}\ell(s_v,y_v)
+\mu \left\|\Pi_{H^1}(\delta^0 s)\right\|^2
\right],
\]

where \(\Pi_{H^1}\) is the orthogonal projection onto the harmonic subspace

\[
H^1\cong \ker L_1,\qquad
L_1=\delta^0\delta^{0*}+\delta^{1*}\delta^1.
\]

The term \(\|\Pi_{H^1}(\delta^0 s)\|^2\) penalizes the cohomological obstruction.

### Algorithmic steps

1. Partition the ARC grid into overlapping local neighborhoods \(\{N_v\}_{v\in V}\).
2. For each \(N_v\), enumerate local DSL program fragments and embed them into \(\mathcal{F}(v)\).
3. For each edge \(e=(v,w)\), define restriction maps \(\rho_{v,e},\rho_{w,e}\) by comparing overlap predictions.
4. Assemble \(\delta^0\) and \(\delta^1\).
5. Compute \(H^1\) via the sheaf Laplacian \(L_1\). If \(H^1\neq 0\), use harmonic representatives to locate inconsistent edges.
6. Refine or prune local fragments on those edges until \(H^1=0\) or the harmonic penalty is minimized.
7. Solve the least-squares objective for \(s^*\), then decode \(s^*\) into a global program.

---

## 2. Poincaré Hyperbolic Geodesic Pruning

### Formulation

Embed program prefixes into the Poincaré ball

\[
\mathbb{B}^d=\{z\in\mathbb{R}^d:\|z\|<1\}.
\]

The Poincaré geodesic distance is

\[
d_P(u,v)=
\operatorname{arcosh}\left(
1+
\frac{2\|u-v\|^2}{(1-\|u\|^2)(1-\|v\|^2)}
\right).
\]

Let \(T\) be a program search tree. Each node \(n\) has:

- partial program \(p_n\),
- hyperbolic embedding \(z_n=\Phi(p_n)\in\mathbb{B}^d\),
- target embedding \(z_t=\Phi(D)\) from the ARC input-output examples.

Define the subtree radius recursively:

\[
R_n=
\max_{c\in \mathrm{children}(n)}
\left(
d_P(z_n,z_c)+R_c
\right),
\qquad
R_{\mathrm{leaf}}=0.
\]

The geodesic ball

\[
B_n=\{z\in\mathbb{B}^d:d_P(z,z_n)\le R_n\}
\]

contains the embeddings of all complete programs in the subtree of \(n\).

Let the target ball be

\[
T_\varepsilon=\{z\in\mathbb{B}^d:d_P(z,z_t)\le \varepsilon\}.
\]

### Pruning rule

If

\[
d_P(z_n,z_t)>R_n+\varepsilon,
\]

then \(B_n\cap T_\varepsilon=\varnothing\), so no completion of \(p_n\) can reach the target. Prune node \(n\).

### Search priority

Use the geodesic distance to the target plus a complexity penalty:

\[
\pi(n)=d_P(z_n,z_t)+\lambda L(p_n),
\]

where \(L(p_n)\) is the description length of the partial program.

### Algorithmic steps

1. Train a hyperbolic encoder \(\Phi\) on DSL programs and ARC tasks.
2. Initialize the root node with empty program \(p_0\), embedding \(z_0\), and radius \(R_0\).
3. For each node \(n\), compute \(z_n\) and \(R_n\) recursively.
4. Prune \(n\) if \(d_P(z_n,z_t)>R_n+\varepsilon\).
5. Expand the unpruned node with smallest priority \(\pi(n)\).
6. Stop when \(d_P(z_n,z_t)\le \varepsilon\) and \(p_n\) is a complete program.

---

## 3. Minimum Description Length Bayesian Search Trees

### Formulation

Let the DSL be equipped with a probabilistic context-free grammar. For a production rule \(r\) expanding nonterminal \(A\), let its probability be

\[
\pi(r\mid A).
\]

A program \(p\) has prior probability

\[
P(p)=\prod_{r\in \mathrm{derivation}(p)} \pi(r\mid A).
\]

The program description length is

\[
L(p)=-\log_2 P(p).
\]

For exact ARC tasks, the likelihood is

\[
P(D\mid p)=
\prod_{(x,y)\in D}
\mathbf{1}[p(x)=y].
\]

For noisy or continuous tasks, use a Gaussian likelihood:

\[
-\log_2 P(D\mid p)
=
\frac{1}{2\sigma^2\ln 2}
\sum_{(x,y)\in D}\|y-p(x)\|^2
+
\mathrm{const}.
\]

The MDL objective is

\[
p^*=
\arg\min_p
\left[
L(p)+L(D\mid p)
\right]
=
\arg\min_p
\left[
-\log_2 P(p)-\log_2 P(D\mid p)
\right].
\]

### Bayesian search tree

For a node \(n\) with partial program \(p_n\), let \(C(n)\) be the set of all completions of \(p_n\). Define the subtree posterior mass

\[
M(n)=
\sum_{c\in C(n)}
P(p_n c)P(D\mid p_n c).
\]

Recursively,

\[
M(n)=
\begin{cases}
P(p_n)P(D\mid p_n), & p_n \text{ complete},\\[4pt]
\sum_{r\in \mathcal{R}(p_n)} M(n_r), & \text{otherwise},
\end{cases}
\]

where \(n_r\) is the child obtained by applying rule \(r\).

The MDL lower bound for node \(n\) is

\[
\mathrm{LB}(n)=-\log_2 M(n).
\]

This is a valid lower bound on the MDL cost of any complete program in the subtree of \(n\).

### Pruning rule

Let \(C_{\mathrm{best}}\) be the MDL cost of the best complete program found so far. Prune node \(n\) if

\[
\mathrm{LB}(n)\ge C_{\mathrm{best}}.
\]

### Algorithmic steps

1. Define the DSL grammar and production probabilities \(\pi(r\mid A)\).
2. Initialize the root node with empty program; set \(C_{\mathrm{best}}=\infty\).
3. For each node \(n\):
   - compute \(L(p_n)\);
   - if \(p_n\) is complete, execute it on the examples and compute \(C(p_n)\);
   - update \(C_{\mathrm{best}}\) if \(C(p_n)<C_{\mathrm{best}}\).
4. Compute the recursive subtree mass \(M(n)\) and lower bound \(\mathrm{LB}(n)\).
5. Prune \(n\) if \(\mathrm{LB}(n)\ge C_{\mathrm{best}}\).
6. Expand the unpruned node with smallest \(\mathrm{LB}(n)\).
7. Return the complete program with minimal MDL cost.

---

These three formulations give a mathematically rigorous pipeline: sheaf cohomology detects local-to-global obstructions, hyperbolic geodesic pruning shapes the search space, and MDL Bayesian search trees provide the optimal program under a probabilistic grammar.

---

## Qwen-3.5 397B (Cloud): Imperfect Information MCTS & Hungarian Deformable Matching
**Duration**: 74.42s

This request combines several advanced algorithmic frameworks. It is important to clarify that while the individual components (ISMCTS, CFR, Kalman, Hungarian, TPS) are well-defined, the specific combinations you requested represent **hybrid research architectures** rather than single, canonical algorithms with universally standardized equations.

Below are the mathematical formulations for constructing these systems based on current State-of-the-Art (SOTA) literature. These formulations synthesize the components into cohesive pipelines suitable for implementation.

---

### 1. Information-Set MCTS with Regret-Matching Policy Priors (ISMCTS-RM)

**Context:** Standard ISMCTS handles imperfect information by sampling determinizations. Standard CFR minimizes regret over information sets. A "bleeding-edge" hybrid uses **Regret Matching (RM)** to bias the ISMCTS tree policy, effectively creating a *Regret-Guided ISMCTS*. This reduces the variance of determinization sampling.

#### 1.1 Core Formulation
Let $I$ be an information set. Let $A(I)$ be the set of available actions.
We maintain cumulative regret $R_T(I, a)$ for action $a \in A(I)$ at iteration $T$.

**Regret Matching Update (CFR Component):**
The regret at iteration $T+1$ is updated based on the counterfactual value $v_i^{\sigma}(I)$:
$$ R_{T+1}(I, a) = \max\left(0, R_T(I, a) + v_i^{\sigma}(I, a) - v_i^{\sigma}(I) \right) $$
Where $v_i^{\sigma}(I)$ is the value of the information set under strategy $\sigma$.

**ISMCTS Selection Policy (RM-Biased UCT):**
Instead of standard UCT, the tree policy $\pi_{tree}$ uses the regret-matched probabilities as a prior $P(I, a)$:
$$ P_{T}(I, a) = \frac{R_T^+(I, a)}{\sum_{b \in A(I)} R_T^+(I, b)} \quad \text{where } R^+ = \max(0, R) $$
If $\sum R^+ = 0$, use uniform distribution.

The selection score $Q_{RM-UCT}$ for node $a$ becomes:
$$ Q_{RM-UCT}(a) = \frac{W_a}{N_a} + c_{puct} \cdot P_T(I, a) \cdot \frac{\sqrt{N_{parent}}}{1 + N_a} $$
Where $W_a$ is total reward, $N_a$ is visit count, and $c_{puct}$ controls exploration.

**Determinization Sampling Bound:**
To limit the "strategy fusion" problem in ISMCTS, we bound the number of determinizations $K$ per information set using the regret convergence rate:
$$ K \geq \frac{C \cdot |A(I)|^2}{\epsilon^2} $$
Where $\epsilon$ is the target exploitability bound and $C$ is a game-specific constant.

#### 1.2 Algorithmic Complexity
*   **Per Iteration:** $O(D \cdot |A|)$, where $D$ is tree depth and $|A|$ is branching factor.
*   **Regret Update:** $O(|I| \cdot |A(I)|)$ per information set visited.
*   **Total Convergence:** To reach $\epsilon$-equilibrium, standard CFR requires $O(1/\epsilon^2)$. ISMCTS-RM improves practical convergence in large trees but retains theoretical complexity of **$O(N \cdot D \cdot |A|)$** for $N$ simulations.
*   **Memory:** $O(|\mathcal{I}| \cdot |A|)$, where $|\mathcal{I}|$ is the number of reachable information sets.

---

### 2. 3D Cell Tracking: Kalman-Hungarian-TPS Pipeline

**Context:** Tracking cells in 3D Biohub data requires handling motion (Kalman), identity association (Hungarian), and tissue deformation (TPS). A robust formulation treats this as a **Joint Spatiotemporal Optimization**.

#### 2.1 Core Formulation

**Step 1: Kalman Prediction (State Estimation)**
For cell $i$ at time $t$, state vector $x_t = [p_x, p_y, p_z, v_x, v_y, v_z]^T$.
$$ \hat{x}_{t|t-1} = F x_{t-1|t-1} $$
$$ P_{t|t-1} = F P_{t-1|t-1} F^T + Q $$
Where $F$ is the motion model and $Q$ is process noise.

**Step 2: TPS Warping (Non-Rigid Correction)**
Before association, correct global tissue drift using Thin-Plate Splines. Let control points be $\{c_k\}$ with displacements $\{d_k\}$. The warping function $f(p)$ minimizes bending energy:
$$ E_{TPS} = \iint \left[ \left(\frac{\partial^2 f}{\partial x^2}\right)^2 + 2\left(\frac{\partial^2 f}{\partial x \partial y}\right)^2 + \left(\frac{\partial^2 f}{\partial y^2}\right)^2 \right] dx dy $$
In 3D, the transformation of a point $p$ is:
$$ f(p) = A p + \sum_{k=1}^{K} w_k U(\|p - c_k\|) $$
Where $U(r) = r^2 \log r^2$ is the kernel, and weights $w_k$ are solved via linear system $L w = d$.

**Step 3: Hungarian Association (Cost Matrix)**
Construct cost matrix $C_{ij}$ between predicted tracks $i$ and detections $j$ (after TPS warping).
$$ C_{ij} = \lambda_m \cdot M_{ij} + \lambda_k \cdot K_{ij} + \lambda_a \cdot A_{ij} $$
*   $M_{ij}$: Mahalanobis distance from Kalman innovation $(z_j - H\hat{x}_{i})^T S^{-1} (z_j - H\hat{x}_{i})$.
*   $K_{ij}$: Appearance similarity (e.g., cosine distance of CNN embeddings).
*   $A_{ij}$: Age penalty (tracks dying/being born).

The optimal assignment $\pi^*$ minimizes total cost:
$$ \pi^* = \arg \min_{\pi \in \Pi} \sum_{i} C_{i, \pi(i)} $$
Solved via the Munkres algorithm.

**Step 4: Kalman Smoothing (RTS Smoother)**
After association, refine trajectories backward ($t = T \to 1$):
$$ G_t = P_{t|t} F^T P_{t+1|t}^{-1} $$
$$ x_{t|T} = x_{t|t} + G_t (x_{t+1|T} - \hat{x}_{t+1|t}) $$
$$ P_{t|T} = P_{t|t} + G_t (P_{t+1|T} - P_{t+1|t}) G_t^T $$

#### 2.2 Algorithmic Complexity
*   **Kalman Filter/Smooth:** $O(T \cdot d^3)$ per track, where $T$ is time steps, $d$ is state dimension (6 for 3D).
*   **TPS Solve:** $O(K^3)$ where $K$ is number of control points (typically $K \ll N_{cells}$).
*   **Hungarian Matching:** $O(N^3)$ per frame, where $N$ is number of active tracks/detections.
*   **Total Per Frame:** **$O(N^3 + K^3)$**.
*   **Memory:** $O(N \cdot T)$ for storing trajectory history for smoothing.

---

### Implementation Considerations & Trade-offs

1.  **ISMCTS-RM Stability:** Pure Regret Matching can be unstable in early iterations. In practice, you must blend the RM prior with UCT exploration using a decay factor $\alpha_T$:
    $$ P_{final} = (1 - \alpha_T) P_{UCT} + \alpha_T P_{RM} $$
    Where $\alpha_T$ decreases as $T \to \infty$.

2.  **TPS Control Points:** For Biohub data, control points for TPS should not be static. They should be selected as **high-confidence tracked cells** (e.g., cells with low Kalman innovation) to model tissue deformation dynamically.

3.  **Parallelization:**
    *   **ISMCTS:** Determinizations can be parallelized across threads (Root Parallelization).
    *   **Tracking:** Kalman updates are independent per track; Hungarian matching is the serial bottleneck. Use Jonker-Volgenant algorithm for faster $O(N^2)$ average case association if $N$ is large.

### References for Further Study
*   **ISMCTS:** Cowling, P. I., et al. "Information Set Monte Carlo Tree Search." *IEEE Transactions on CIG* (2012).
*   **CFR:** Zinkevich, M., et al. "Regret Minimization in Games with Incomplete Information." *NIPS* (2008).
*   **Tracking:** Wojke, N., et al. "Simple Online and Realtime Tracking with a Deep Association Metric." *ICIP* (2017) (For cost matrix formulation).
*   **TPS:** Bookstein, F. L. "Principal Warps: Thin-Plate Splines and the Decomposition of Deformations." *IEEE TPAMI* (1989).

*Disclaimer: These formulations represent a synthesis of SOTA components. Specific hyperparameters ($\lambda$, $c_{puct}$, $Q$ noise) require tuning on your specific dataset or game ruleset.*

---

## GLM-5.2 (Cloud): Multi-View 3D DICOM Focal Loss & HIHO 0.5 Coherence
**Duration**: 68.14s

Here are the bleeding-edge mathematical formulations for both the multi-view 3D DICOM feature fusion with asymmetric focal loss, and the 12-parameter quadrature field stability at the 0.5 HIHO coherence point.

---

### Part 1: Multi-view 3D DICOM Feature Fusion with Asymmetric Focal Loss

For RSNA Knee abnormality detection, we process three orthogonal 3D DICOM volumes: Sagittal ($X_s$), Coronal ($X_c$), and Axial ($X_a$). We utilize a multi-view cross-attention fusion mechanism followed by an asymmetric focal loss to handle the severe class imbalance inherent in knee abnormalities (e.g., ACL tears vs. healthy).

#### 1. Feature Extraction and Cross-View Fusion
Let $f_{\theta_v}: \mathbb{R}^{D \times H \times W} \rightarrow \mathbb{R}^d$ be the 3D CNN feature extractor for view $v \in \{s, c, a\}$. 
The latent representations are:
$$ Z_v = f_{\theta_v}(X_v) \in \mathbb{R}^d $$

We compute cross-view attention weights to dynamically fuse the views based on pathological relevance:
$$ A = \text{Softmax}(W_{att} [Z_s, Z_c, Z_a] + b_{att}) \in \mathbb{R}^{3 \times d} $$
$$ F = \sum_{v \in \{s,c,a\}} A_v \odot Z_v \in \mathbb{R}^d $$

The final abnormality probability is $p = \sigma(W_{cls} F + b_{cls})$, where $\sigma$ is the sigmoid function.

#### 2. Asymmetric Focal Loss (AFL) Formulation
To address the asymmetry between easy/hard and positive/negative samples, we define class-dependent focusing parameters $\gamma_+$ (for abnormalities) and $\gamma_-$ (for healthy), and a balancing factor $\alpha$.

Let $y \in \{0, 1\}$ be the ground truth. The probability $p_t$ is defined as $p_t = p$ if $y=1$, and $p_t = 1-p$ if $y=0$. The Asymmetric Focal Loss is:
$$ \mathcal{L}_{AFL}(p, y) = - y \alpha (1-p)^{\gamma_+} \log(p) - (1-y)(1-\alpha) p^{\gamma_-} \log(1-p) $$

#### 3. Exact Loss Gradients
Let $z = W_{cls} F + b_{cls}$ be the logit, such that $p = \sigma(z) = \frac{1}{1+e^{-z}}$. The derivative of the sigmoid is $\frac{\partial p}{\partial z} = p(1-p)$.

First, compute the derivative w.r.t $p$:
$$ \frac{\partial \mathcal{L}_{AFL}}{\partial p} = y \alpha \left[ \gamma_+ (1-p)^{\gamma_+ - 1} \log(p) - \frac{(1-p)^{\gamma_+}}{p} \right] - (1-y)(1-\alpha) \left[ -\gamma_- p^{\gamma_- - 1} \log(1-p) - \frac{p^{\gamma_-}}{1-p} \right] $$

Applying the chain rule $\frac{\partial \mathcal{L}_{AFL}}{\partial z} = \frac{\partial \mathcal{L}_{AFL}}{\partial p} p(1-p)$, the exact gradient w.r.t the logit $z$ is:
$$ \frac{\partial \mathcal{L}_{AFL}}{\partial z} = y \alpha \left[ \gamma_+ p(1-p)^{\gamma_+} \log(p) - (1-p)^{\gamma_+ + 1} \right] + (1-y)(1-\alpha) \left[ \gamma_- (1-p)p^{\gamma_-} \log(1-p) + p^{\gamma_- + 1} \right] $$

The gradient propagates back to the fused feature $F$ via $\frac{\partial \mathcal{L}}{\partial F} = \frac{\partial \mathcal{L}}{\partial z} W_{cls}^T$, and subsequently distributes to the view-specific extractors via the attention Jacobian.

---

### Part 2: 12-Parameter Quadrature Field Stability at 0.5 HIHO Coherence

We define a 12-dimensional parameter space $\Theta = [\theta_1, \theta_2, \dots, \theta_{12}]^T \in \mathbb{R}^{12}$. These parameters modulate a complex quadrature field $\Phi(\mathbf{x}; \Theta)$. We partition the 12 parameters into two orthogonal quadrature subspaces: $\Theta_1 = [\theta_1, \dots, \theta_6]^T$ (in-phase) and $\Theta_2 = [\theta_7, \dots, \theta_{12}]^T$ (quadrature).

#### 1. Quadrature Field and HIHO Coherence Metric
The field energy is defined by the squared norms of the parameter subspaces:
$$ S_1 = \|\Theta_1\|^2 = \sum_{i=1}^6 \theta_i^2, \quad S_2 = \|\Theta_2\|^2 = \sum_{i=7}^{12} \theta_i^2 $$

The High-Index High-Order (HIHO) coherence metric $C_{HIHO} \in [-1, 1]$ measures the phase-space energy balance:
$$ C_{HIHO}(\Theta) = \frac{S_1 - S_2}{S_1 + S_2} $$

The **0.5 HIHO coherence point** represents a critical stability equilibrium where the in-phase energy is exactly three times the quadrature energy:
$$ C_{HIHO}(\Theta^*) = 0.5 \implies \frac{S_1 - S_2}{S_1 + S_2} = 0.5 \implies S_1 = 3 S_2 $$

#### 2. Stability Loss Formulation
To maintain stability around this 0.5 coherence point, we define a loss function that penalizes both deviation from the target coherence and high parametric sensitivity (Jacobian norm) to ensure flat-minima stability:
$$ \mathcal{L}_{stab}(\Theta) = \lambda_1 (C_{HIHO}(\Theta) - 0.5)^2 + \lambda_2 \sum_{i=1}^{12} \left( \frac{\partial C_{HIHO}}{\partial \theta_i} \right)^2 $$

#### 3. Exact Stability Gradients
First, we derive the partial derivatives of the coherence metric:
For $i \in \{1, \dots, 6\}$:
$$ \frac{\partial C}{\partial \theta_i} = \frac{2\theta_i(S_1+S_2) - (S_1-S_2)(2\theta_i)}{(S_1+S_2)^2} = \frac{4\theta_i S_2}{(S_1+S_2)^2} $$

For $i \in \{7, \dots, 12\}$:
$$ \frac{\partial C}{\partial \theta_i} = \frac{-2\theta_i(S_1+S_2) - (S_1-S_2)(2\theta_i)}{(S_1+S_2)^2} = \frac{-4\theta_i S_1}{(S_1+S_2)^2} $$

The gradient of the stability loss w.r.t any parameter $\theta_i$ is computed via the chain rule:
$$ \frac{\partial \mathcal{L}_{stab}}{\partial \theta_i} = 2 \lambda_1 (C_{HIHO} - 0.5) \frac{\partial C}{\partial \theta_i} + 2 \lambda_2 \sum_{j=1}^{12} \frac{\partial C}{\partial \theta_j} \frac{\partial^2 C}{\partial \theta_i \partial \theta_j} $$

Where the second-order partial derivatives (Hessian elements of $C$) are:
For $i, j \in \{1, \dots, 6\}$:
$$ \frac{\partial^2 C}{\partial \theta_i \partial \theta_j} = \frac{4 S_2 \delta_{ij}}{(S_1+S_2)^2} - \frac{16 \theta_i \theta_j S_2}{(S_1+S_2)^3} $$

For $i, j \in \{7, \dots, 12\}$:
$$ \frac{\partial^2 C}{\partial \theta_i \partial \theta_j} = \frac{-4 S_1 \delta_{ij}}{(S_1+S_2)^2} - \frac{16 \theta_i \theta_j S_1}{(S_1+S_2)^3} $$

For $i \in \{1, \dots, 6\}$ and $j \in \{7, \dots, 12\}$ (and vice versa):
$$ \frac{\partial^2 C}{\partial \theta_i \partial \theta_j} = \frac{4 \theta_i (S_1 - 3S_2)}{(S_1+S_2)^3} \quad \text{(evaluated at the 0.5 point, this cross-term vanishes since } S_1 = 3S_2 \text{)} $$

By optimizing $\Theta$ via gradient descent on $\mathcal{L}_{stab}$, the 12-parameter field converges to a highly stable manifold exactly at the 0.5 HIHO coherence threshold.

---

