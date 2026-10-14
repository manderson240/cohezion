# Adversarial Portfolio Review: manderson240
## Unsparing Critique & Gap Analysis

---

## 1. ARC Prize 2026: ARC-AGI-2 (31.81%, Rank 245)

### 1.1 Theoretical & Practical Ceilings

**The fundamental self-deception: Your approach is a DSL-first, TTT-second hybrid, and you're betting on the *wrong* modality.**

At 83.61%, Top 1 is almost certainly running a **full program synthesis search** — not LoRA SFT + DSL injection. The Qwen3-4B LoRA SFT139 is approximating a distribution over DSL programs via behavioral cloning, but:

- **SFT on program synthesis is reward-hacked generalization.** You're learning P(program | input_output) as a supervised conditional, but the MAP estimator under SFT loss ≠ the MPE under test-time search. The entropy of the posterior over programs given a novel task is enormous, and 4B parameters with LoRA cannot represent it. You're collapsing a search problem into a generation problem.

- **TTT (Test-Time Training) on ARC-AGI-2 has a theoretical ceiling dictated by the information content of the task's I/O pairs.** If the task has 2-3 training examples and the transformation is compositional with ≥4 primitives, the Bayesian posterior over the correct program given those examples is still near-uniform over a combinatorial space. TTT fine-tunes toward the training examples but cannot resolve the ambiguity — it sharpens P(program | train_examples) without increasing the mutual information I(program; test_solution | train_examples).

- **Monotonic Attempt-2 DSL injection with D4 invariant filtering** — this is where the real signal is, but you've shackled it to "Attempt-2" only. The D4 invariant filtering (checking solutions under the dihedral group of order 8) is sound, but you're applying it as a *post-hoc rejection* rather than as a *search prior*. Leaders are likely using D4 invariance (and broader symmetry groups — translation, color permutation) to **factor the search space** by symmetry orbits *before* generating candidate programs.

### 1.2 What Leaders Are Doing

**Top 1 at 83.61% is not doing what you're doing.** The gap from 31.81% to 83.61% is 51.8 percentage points — that's not a tuning gap, it's a paradigm gap. Candidates:

1. **Neurosymbolic program synthesis with typed λ-calculus or relational DSLs** that support higher-order primitives (map, fold, filter, compose) — not flat grid-operation DSLs. The compositional expressivity of a higher-order DSL is exponentially greater, and it's what's needed for ARC-AGI-2's harder tasks.

2. **MCTS / beam search over program space with a learned policy + value head**, not SFT generation + filtering. The value head estimates P(solution correct | partial_program, task), enabling branch-and-bound. You have no value head. You have a policy (Qwen3-4B) but no search.

3. **LLM-as-synthesizer with explicit chain-of-thought program construction and verification loop** — GPT-4o/Claude class models running iterative refinement: propose → execute on train → compare → repair. This is fundamentally different from your "fine-tune a small model to generate programs once." The repair loop is where the accuracy comes from.

4. **Likely using a frontier model (GPT-4o, Claude 3.5/Opus) via API, not a local 4B model.** The 83.61% score is consistent with frontier-model CoT + verification. Your 4B LoRA model is information-theoretically incapable of matching this — the knowledge gap between Qwen3-4B and Claude Opus on abstract reasoning is not bridgeable by LoRA on 139 tasks.

### 1.3 Failure Modes & Overfitting Risks

- **D4 invariant filtering can reject correct solutions** when the task's output is only *partially* symmetric, or when the symmetry is in the *process* not the *output*. You're filtering on output-space D4 invariance, but ARC tasks frequently have process-space symmetries that don't manifest in output D4 invariance.

- **LoRA SFT139 overfits to the training task distribution.** The 139-task training set is tiny and biased toward certain transformation families. The model learns frequency-weighted priors over program types, which systematically disadvantages rare transformation types. This is exactly the failure mode that hurts on the long tail.

- **TTT on test-time examples risks catastrophic forgetting** of the base model's reasoning patterns, particularly with 4B parameters. The fine-tuning signal from 2-3 examples is too weak to override the base distribution without distorting it.

- **Monotonic Attempt-2 DSL injection** assumes Attempt-1 has useful structure to build on. If Attempt-1 is garbage (which it will be for ~50%+ of tasks given your accuracy), you're injecting DSL candidates into a corrupted context. This is a bootstrap problem you haven't addressed.

### 1.4 Highest-Leverage Breakthroughs

**Breakthrough 1: Replace SFT with MCTS-guided program synthesis.** Train a value head (small transformer or MLP) on (partial_program, task) → P(correct) using self-play on the training set. Run beam search / MCTS at test time with the value head as heuristic. This is the single highest-leverage change — it converts your pipeline from open-loop generation to closed-loop search, which is necessary for the compositional tasks.

**Breakthrough 2: Use a frontier model (Claude Opus / GPT-4o) as the program proposer, with your DSL as the execution backend.** The competition rules likely permit external API calls (verify this). If so, your 4B model is a self-imposed handicap. Use the frontier model's CoT to propose DSL programs, execute them, verify against train examples, and iterate. Your DSL + D4 filtering + execution engine become the *verification harness* for the frontier model's proposals.

**Breakthrough 3: Symmetry-quotiented program search.** Instead of generating full programs and filtering by D4, generate programs in the symmetry-quotiented space. Define equivalence classes of programs under the action of D4 × color_permutation × translation on the output. Search one representative per equivalence class. This reduces the effective branching factor by O(|G|) where |G| can be 8 × k! × (H×W) for rich symmetry groups.

---

## 2. Enveda CASMI26 Molecule ID (0.421 MRR, Rank 425)

### 2.1 Theoretical & Practical Ceilings

**The fundamental self-deception: You're treating this as a retrieval problem with structural priors, but it's actually a generative molecular structure elucidation problem.**

At 0.484 MRR, Top 1 is close to the theoretical ceiling for MS/MS-only identification (the mass spec doesn't uniquely determine structure in many cases — MRR ≤ 1.0 is bounded by the inherent ambiguity of MS/MS fragmentation). The gap from 0.421 to 0.484 is 0.063 MRR — that's 13% relative improvement, which is substantial but achievable.

Your pipeline: 4-channel analog propagation + MetFrag-lite + PubChem candidate join + POP_MU popularity prior + RDKit tautomer canonicalization.

**Critical issue: Your candidate universe is PubChem, which is ~118M molecules but excludes many metabolites and natural products.** CASMI challenges historically feature natural products, drugs, and metabolites — these are systematically under-represented in PubChem relative to synthetic compounds. If your candidate pool is PubChem-filtered, you have a coverage problem on the exact molecules CASMI targets.

**POP_MU popularity prior is a double-edged sword.** It biases toward well-known molecules, which helps for common drugs/metabolites but penalizes the long tail of obscure natural products that CASMI specifically uses as "difficult" cases. You're optimizing for the mode of the distribution while the competition is scored on the full distribution including the tail.

### 2.2 What Leaders Are Doing

**Top 5 at 0.455+ are almost certainly using one or more of:**

1. **MassFormer / GraFFMs / Spectrum2Structure generative models** — neural networks that map MS/MS spectra → molecular fingerprints → structure. These are generative, not retrieval-based, so they don't depend on candidate coverage. The fingerprint → structure step uses a graph generative model (e.g., GraphINVENT) or a beam search over molecular graph space.

2. **CFM-ID (Competitive Fragmentation Model) for spectrum prediction + database matching** — the state-of-the-art approach. CFM-ID *predicts* the MS/MS spectrum for each candidate molecule and then compares predicted vs. observed spectra. This is the reverse of your approach (you propagate observed spectrum features to candidates; they predict what the spectrum *should* look like for each candidate and compare). CFM-ID's predicted spectra are highly informative because they model the fragmentation physics.

3. **Multi-stage reranking with a contrastive learned embedding** — SIRIUS+CSI:FingerID is the gold standard. It combines:
   - Molecular formula determination from isotope pattern + MS1
   - CSI:FingerID: a deep neural network mapping spectrum → molecular fingerprint (1000+ molecular descriptors)
   - Database search using the predicted fingerprint
   This pipeline has been benchmarked on CASMI and consistently outperforms MetFrag-based approaches.

4. **Ensemble of MetFrag + CFM-ID + CSI:FingerID with learned fusion weights.** The leaders are probably not betting on a single approach — they're ensembling multiple orthogonal predictors.

### 2.3 Failure Modes & Overfitting Risks

- **4-channel analog propagation** — this is the weakest link. "Analog propagation" assumes that structurally similar molecules have similar fragmentation patterns. This is *approximately* true but fails systematically for:
  - Molecules with different functional group arrangements (e.g., ortho vs. para substitution)
  - Stereoisomers (different 3D geometry → different fragmentation energetics)
  - Molecules where the fragmentation-determining bond is in a different structural context
  
  You're propagating in a 4-channel representation that likely captures some of this, but the fundamental assumption breaks at exactly the hard cases that separate top teams.

- **MetFrag-lite fragment parsimony** — MetFrag's fragment matching is based on combinatorial bond breaking, which is computationally expensive and uses a simplified fragmentation model. It doesn't account for:
  - Rearrangements (McLafferty, retro-Diels-Alder)
  - Radical-driven fragmentations
  - Charge-remote fragmentation
  
  The "lite" version presumably further simplifies this. You're missing the physical fragmentation pathways that dominate for many compound classes.

- **RDKit tautomer canonicalization** — this is necessary but insufficient. RDKit's tautomer enumeration is incomplete for many heterocyclic systems and doesn't handle all pH-dependent forms. CASMI molecules often have multiple stable tautomers that produce different MS/MS spectra.

- **Overfitting risk: PubChem candidate join** — if your validation set is also from PubChem-derived molecules, you're overfitting to the candidate pool's distribution. The leaderboard test set likely includes molecules outside PubChem's coverage, where your pipeline has no candidates to rank.

### 2.4 Highest-Leverage Breakthroughs

**Breakthrough 1: Integrate CSI:FingerID-style spectrum → fingerprint prediction.** Train or use a pre-trained deep neural network that maps your MS/MS spectrum → a molecular fingerprint vector (e.g., ECFP4, MACCS, or a learned fingerprint). Then search the candidate database using cosine similarity in fingerprint space. This is fundamentally different from your analog propagation — it's a learned mapping that captures fragmentation physics implicitly through training data, rather than an explicit graph-propagation heuristic. Use the open-source SIRIUS 5 framework if the license permits.

**Breakthrough 2: Add CFM-ID-style spectrum prediction as a reranking signal.** For your top-N candidates (N=50-100), predict their MS/MS spectra using a fragmentation model and compare to the observed spectrum. This gives an orthogonal scoring signal to your analog propagation. The predicted-vs-observed spectral similarity is highly discriminative because it directly models the physics. Even a simplified CFM-ID (predicting top-10 fragments per molecule) would add significant signal.

**Breakthrough 3: Expand candidate universe beyond PubChem.** Add COCONUT (natural products), ChEBI (metabolites), DrugBank, and KEGG to your candidate pool. CASMI targets these compound classes specifically. The candidate universe expansion alone could recover 3-5% MRR from molecules you currently have no chance of identifying. Apply the popularity prior *within* each database, not globally — a natural product from COCONUT shouldn't be penalized for being less popular than a drug from PubChem.

---

## 3. RSNA Knee Abnormality Detection (0.943 AUC, Rank 1,242)

### 3.1 Theoretical & Practical Ceilings

**The fundamental self-deception: Your Kolmogorov Monotonicity Projection P(Abnormal) >= max P_k is a mathematical constraint that's clinically wrong.**

Your model predicts per-slice or per-view probabilities P_k for different abnormalities, then projects to enforce P(Abnormal) >= max_k P_k. This enforces a monotone relationship: if any individual abnormality is present, the "any abnormality" label must be at least as likely. **But this is not how multi-label medical imaging works.**

The clinical reality:
- A knee can have a subtle combination of sub-threshold findings that collectively indicate abnormality even when no single finding exceeds threshold.
- Conversely, a single high-confidence finding (e.g., clear effusion) may be a false positive for that specific abnormality but correctly indicates "abnormal."
- The max-k projection assumes the "any abnormality" label is a logical OR of the individual findings. In practice, the ground truth may be generated from a different diagnostic criterion than the individual labels, introducing label noise that your monotonicity assumption cannot capture.

**At 0.964 AUC, Top 1 is near the theoretical ceiling for this task.** The 0.021 AUC gap (0.943 → 0.964) is roughly 1.5% of the remaining achievable range (0.943 → 1.0). This is a *modeling* gap, not an architecture gap.

### 3.2 What Leaders Are Doing

**Top 5 at 0.963+ are almost certainly using:**

1. **3D vision transformers (e.g., SwinUNETR, ViT-3D) with pre-training on large medical datasets.** Your CoAtNet/Raptor backbones are 2D or 2.5D at best. The knee MRI volumes are inherently 3D, and the spatial relationships between slices carry diagnostic information (e.g., the progression of a meniscal tear across slices). 2D backbones with 32-slice aggregation lose this.

2. **Contrastive pre-training on the full RSNA dataset (self-supervised).** SimCLR, MoCo, or BYOL on the unlabeled knee MRIs before fine-tuning. This extracts additional signal from the data distribution itself. Your approach starts from ImageNet or random initialization and fine-tunes on the labeled set only — you're leaving free information on the table.

3. **Multi-task learning with auxiliary objectives:** predicting slice position, predicting laterality (left/right knee), predicting image quality, and predicting the sequence type (PD, T1, T2). These auxiliary tasks regularize the representation and improve the primary task.

4. **Test-time augmentation (TTA) with geometric + intensity transforms applied to the 3D volume.** Your quantile rank normalization is a *post-hoc* ensemble technique, not TTA. Leaders average predictions over multiple augmented versions of each volume, which reduces variance and improves calibration.

5. **Expert-designed features from radiomics or anatomical landmarks.** Knee MRI has well-defined anatomical structures (medial/lateral meniscus, ACL, PCL, cartilage). Leaders may be incorporating anatomical priors — e.g., a knee landmark detector that crops the volume to the joint space before classification.

### 3.3 Failure Modes & Overfitting Risks

- **Multi-resolution (r224+r336) ensemble** — this is a poor man's multi-scale. The two resolutions are processing the *same* volume at different input sizes, not extracting features at different *receptive field* scales within a single forward pass. A proper multi-scale approach uses feature pyramid networks or dilated convolutions at multiple rates. You're paying 2× compute for marginal diversity gain.

- **Intra-column quantile rank normalization** — this normalizes predictions within a column (presumably a patient or study), which assumes the within-study distribution is informative. But if a study has all normal slices, quantile rank normalization will artificially spread the predictions, creating false positives. This is a normalization artifact, not a signal.

- **CoAtNet backbone** — CoAtNet is a 2021 architecture designed for ImageNet classification. It's not specialized for medical imaging and doesn't handle 3D volumes natively. You're applying a generic 2D architecture to a domain-specific 3D problem.

- **Overfitting risk: 32-slice volumetric depth** — 32 slices is a hard truncation. Knee MRI studies often have 30-40+ slices per series. If you're truncating or padding to 32, you're losing information at the boundaries. More importantly, the diagnostic information may be concentrated in specific slices (e.g., the meniscus is best seen in the middle slices), and uniform sampling to 32 slices may miss the diagnostically critical slices.

### 3.4 Highest-Leverage Breakthroughs

**Breakthrough 1: Switch to a 3D backbone (SwinUNETR or nnUNet encoder) with self-supervised pre-training.** SwinUNETR is pre-trained on large medical imaging datasets (BTCV, BraTS) and handles 3D volumes natively. The self-supervised pre-training extracts transferable features that ImageNet-pretrained 2D backbones cannot. This is the single most impactful change. Even without pre-training, a 3D Swin transformer will outperform a 2D CoAtNet on volumetric data by capturing inter-slice dependencies.

**Breakthrough 2: Replace the Kolmogorov monotonicity projection with a learned calibration head.** Instead of hard-coding P(Abnormal) >= max P_k, train a small MLP that takes the per-finding probabilities + their uncertainties (entropy) as input and predicts the calibrated "any abnormality" probability. Let the model learn the correct aggregation function from data, including the cases where sub-threshold findings combine to indicate abnormality. Use temperature scaling + isotonic regression for final calibration.

**Breakthrough 3: Add TTA with 3D augmentations.** Apply random affine transforms (rotation ±15°, translation ±5% in all 3 axes), intensity scaling (±10%), and elastic deformation to the 3D volume. Average predictions over 8-16 augmented versions. This is free AUC (typically +0.005-0.01) and costs only inference time. Your multi-resolution ensemble can be replaced by this, saving training compute while improving diversity.

---

## 4. ARC-AGI-3 Interactive Agent (0.26 best, Rank 2,481)

### 4.1 Theoretical & Practical Ceilings

**The fundamental self-deception: Directed Affordance Rarity Search + Markov anti-cycle penalties is a *local search* framework applied to a *planning* problem.**

At 55.89%, Top 1 is solving these tasks with genuine planning and reasoning, not affordance-guided random walks with cycle avoidance. The gap from 0.26 to 0.56 is 30 percentage points — this is not a tuning gap, it's a capability gap.

**Your approach is fundamentally reactive, not deliberative.** Directed Affordance Rarity Search prioritizes actions by their rarity (exploration bonus), and Markov anti-cycle penalties discourage revisiting states. But:

- **Rarity ≠ Utility.** The rarest affordance is frequently irrelevant or counterproductive. You're exploring the action space by novelty, not by goal-directedness. This is akin to count-based exploration in RL — effective for coverage, terrible for task completion.

- **1/2/3-6 cycle Markov penalties are memory-limited.** A Markov penalty of order k only prevents cycles of length ≤ k. Many ARC-AGI-3 tasks require sequences of 15-50+ actions. Long-range cycles (e.g., revisit a state after 20 steps) are invisible to your penalty. You need full graph-based cycle detection (maintain a visited set), not Markov approximations.

- **SplitMix64 Zobrist hashing** — this is a high-quality hash for board game positions, but ARC-AGI-3 states are richer (grid + agent state + possibly hidden state). Zobrist hashing requires a fixed feature decomposition, and if you're not capturing all state variables, you'll have hash collisions that cause you to miss cycles.

- **Kaggle CPU constraint** — this is the binding constraint. You're running on CPU with a limited compute budget, which rules out LLM-based reasoning (too slow), MCTS with deep rollouts (too slow), and neural network forward passes (too slow on CPU). You're in a regime where only lightweight symbolic methods are feasible.

### 4.2 What Leaders Are Doing

**Top 1 at 55.89% is almost certainly using:**

1. **LLM-based planning with code generation** — the agent generates a Python program that describes the solution strategy, then executes it. This is the approach used by SOTA agents on ARC-AGI-3-like benchmarks (e.g., the work on embodied agents with LLM planners). The LLM (likely GPT-4o or Claude) analyzes the task description + initial state, writes a plan in code, and the code executes the actions. The CPU constraint may not apply if the competition allows API calls — check the rules.

2. **Hierarchical task decomposition** — decomposing the task into subgoals (e.g., "collect all blue objects," "paint the wall," "open the door") and solving each subgoal with a specialized strategy. This is fundamentally different from your flat affordance search — it's a two-level (or multi-level) architecture with a high-level planner and low-level executors.

3. **Goal-conditioned policy with subgoal embeddings** — a neural network that takes (state, subgoal) → action. Even on CPU, a small MLP (128 hidden units) can run fast enough. The key is that the policy is *goal-conditioned*, not just novelty-seeking.

4. **Classical planning (STRIPS/PDDL) with automatic problem encoding** — convert the ARC-AGI-3 task to a PDDL problem and use a classical planner (FF, LAMA, Downward). This is CPU-friendly and leverages decades of planning research. The challenge is the automatic encoding, but if the task structure is regular enough, this is feasible.

### 4.3 Failure Modes & Overfitting Risks

- **Recent runs dropping to 0.10-0.12** — this is a critical red flag. It suggests either:
  (a) Non-determinism in your agent (random seed dependency) — your agent is high-variance, meaning the 0.26 was a lucky run.
  (b) Test set distribution shift — the hidden test set has different task types than your development set.
  (c) A regression in your code — you changed something that broke the pipeline without noticing.
  
  If (a), you need to average over multiple seeds and report the mean, not the max. If (b), you need to analyze which task types you're failing on. If (c), you need version control and regression testing.

- **Directed Affordance Rarity Search has no goal signal.** You're searching by action rarity, not by progress toward the goal. If the task requires a specific sequence of common actions (e.g., move right 10 times, then interact), your rarity search will waste time exploring rare but irrelevant actions.

- **Markov anti-cycle penalties create local optima.** If the only path to the goal requires passing through a state that was visited k steps ago (where k is within your penalty window), your agent will avoid it and get stuck. This is the classic problem with anti-cycle heuristics in maze-like environments.

### 4.4 Highest-Leverage Breakthroughs

**Breakthrough 1: Replace affordance rarity search with LLM-generated plans (if API access is allowed).** For each task, use GPT-4o/Claude to:
1. Describe the task in natural language (from the task specification)
2. Generate a step-by-step plan in structured English
3. Translate the plan into a sequence of actions or a Python script that generates the action sequence
4. Execute and verify against the goal condition

This is the approach that's working at 55%+. Your symbolic search is a dead end for this competition — the tasks require semantic understanding that lightweight symbolic methods cannot provide.

**Breakthrough 2: If no API access is allowed, implement goal-conditioned A* with a learned heuristic.** Even on CPU, A* with a reasonable heuristic can solve tasks with 20-50 action sequences. The heuristic should estimate the distance to the goal state — train it on solved tasks using the actual solution lengths as targets. A small neural network (MLP with 256 hidden units, 3 layers) can serve as the heuristic and run in <1ms on CPU. Combine with full visited-set cycle detection (not Markov approximations).

**Breakthrough 3: Implement automatic PDDL encoding and use a classical planner.** If the task environment has a regular action interface (move, pick up, drop, interact), you can write a PDDL domain once and auto-generate the problem instance from each task's initial state and goal. Feed this to FF or LAMA, which are CPU-optimized and can solve planning problems with 100+ actions in seconds. This is the most compute-efficient approach if the task structure permits automatic encoding.

**Breakthrough 4 (diagnostic): Fix the 0.26 → 0.10-0.12 regression immediately.** Before any architectural changes, determine whether your 0.26 was a fluke. Run your agent 20 times with different seeds on the same task set and compute mean ± std. If the variance is high (>0.05), your 0.26 is not reliable and your actual performance is closer to 0.11. This would fundamentally change your strategic priorities.

---

## 5. Cross-Competition Meta-Analysis

### 5.1 Systemic Pattern: Over-Engineering on Weak Foundations

Across all four competitions, there's a consistent pattern: **you're applying sophisticated post-hoc techniques (D4 filtering, Kolmogorov projection, Markov penalties, analog propagation) on top of weak base models.** This is the competitive ML equivalent of putting a carbon fiber wing on a stock Civic — the advanced components don't compensate for the fundamental inadequacy of the base.

The leaders are doing the opposite: **strong base models (frontier LLMs, 3D medical imaging transformers, CSI:FingerID) with minimal post-processing.** The base model does the heavy lifting; the post-processing is calibration and ensembling, not information extraction.

### 5.2 Compute Allocation

On Quad-L4 GPUs, you're compute-constrained. Your allocation across 4 competitions is likely suboptimal:

- ARC-AGI-2 and ARC-AGI-3 are the highest-value competitions ($700k + $850k = $1.55M total) but also the hardest to crack without frontier models. Consider whether competing on both is diluting your effort.

- RSNA ($77k) and CASMI ($50k) are more tractable and the gaps are smaller (0.021 AUC, 0.063 MRR). These are better ROI per unit effort.

### 5.3 The Frontier Model Question

**The elephant in the room: Are you using frontier models (GPT-4o, Claude Opus) where permitted?** If the competition rules allow external API calls and you're not using them, you're competing with one hand tied behind your back. A 4B LoRA model will never match Claude Opus on abstract reasoning — the parameter count gap is 2 orders of magnitude, and the training data gap is 3 orders of magnitude.

If frontier models are *not* allowed (some ARC competitions restrict this), then you need to acknowledge that your ceiling is lower and optimize accordingly — focus on the symbolic/program synthesis approaches where small models + search can be competitive.

### 5.4 Summary: Priority Actions

| Competition | Current | Top 1 | Gap | #1 Priority Action |
|---|---|---|---|---|
| ARC-AGI-2 | 31.81% | 83.61% | 51.8% | Frontier model CoT + DSL verification loop OR MCTS program synthesis |
| CASMI26 | 0.421 | 0.484 | 0.063 | CSI:FingerID-style spectrum→fingerprint prediction |
| RSNA | 0.943 | 0.964 | 0.021 | 3D SwinUNETR with self-supervised pre-training |
| ARC-AGI-3 | 0.26 | 0.559 | 0.30 | LLM-generated plans (if allowed) or goal-conditioned A* with learned heuristic |

**The unifying thesis: stop optimizing the periphery and fix the core.** Every competition has a clear "upgrade the base model" action that would yield more than all your current post-processing combined.