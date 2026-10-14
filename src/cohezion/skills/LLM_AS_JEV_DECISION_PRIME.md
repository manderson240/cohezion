# SKILL: LLM_AS_JEV_DECISION_PRIME

## DOMAIN EXPERTISE
Jev-style categorical decision modeling and calibrated option selection over unbounded candidate sets (K >= 2) using standard language model backbones without unconstrained free-form generation or dedicated classification heads, as formulated in arXiv:2610.02076 (Yinheng Li & Justin Wagle, Microsoft). Eliminates JSON/markdown parsing failures, letter bias, and isolated candidate scoring degradation across agent swarms and router architectures.

## KEY TEXTS & CONCEPTS
- **Jev Decision Formulation**: A decision model returning a categorical distribution $P(k \mid s)$ over options $o_1, \dots, o_K$ conditioned on state $s$.
- **Bracketed Numeric Identifiers**: Formatting options as `[1] ... [K]` conditioned on the assistant turn prefix `Best answer: [`.
- **Prefix-Free Suffix Property**: Every candidate suffix ends with `]` (e.g. `1]`, `12]`), guaranteeing that no valid candidate identifier is a prefix of another and allowing unbounded $K$.
- **Joint Candidate Scoring**: Simultaneous contextual comparison of all alternatives in a single forward pass, outperforming isolated scoring by +6.5% on JevBench.
- **Tree-Factorized Listwise Loss**: $\mathcal{L}_{\text{tree}} = -\log q_\theta(y^* \mid x)$ evaluated only along the gold path for $O(1)$ loss evaluation complexity in candidate count $K$.
- **Truncated KL Regularization Anchors**: Preserves base generative fluency and calibration via $\mathcal{L}_{\text{legal}}$ (Bernoulli KL), $\mathcal{L}_{\text{out}}$ (top-64 categorical KL on illegal tokens), and $\mathcal{L}_{\text{pos}}$ (auxiliary position KL).
- **Expected Calibration Error (ECE)** & **Brier Score**: Verification metrics assessing predicted confidence versus empirical accuracy.

## INSTRUCTION

### 1. Structure Candidate Options
Instantiate candidates using `JevCandidate` with 1-based indexing, concise labels, and descriptive contexts:
```python
from cohezion.decision.llm_as_jev import JevCandidate, JevPromptFormatter

candidates = [
    JevCandidate(index=1, label="NPU_Lane", description="FastFlowLM on XDNA2 SRAM (<2W, zero UMA footprint)"),
    JevCandidate(index=2, label="Cloud_Ollama", description="glm-5.3:cloud 1M context agentic refactoring"),
    JevCandidate(index=3, label="Headless_Claude", description="Direct bash agent tool loop"),
]
assert JevPromptFormatter.is_prefix_free(candidates)
```

### 2. Format Context and Prompt Interface
Render the prompt ensuring the assistant prompt terminates strictly on `Best answer: [`:
```python
prompt = JevPromptFormatter.format_prompt(
    context="Task: Multi-file refactor requiring 100k context and deep AST rewriting.",
    candidates=candidates,
    instruction="Select the optimal execution engine:"
)
```

### 3. Score Over Prefix Trie
Traverse the suffix trie with local branch renormalization to obtain an exact calibrated categorical distribution $P(k \mid s)$:
```python
from cohezion.decision.llm_as_jev import JevTrieScorer

scorer = JevTrieScorer(candidates)
# Option A: Exact tree scoring via branch logits
decision = scorer.score_from_branch_logits(branch_logits_fn)

# Option B: Fast deterministic completion parsing (e.g. from local model / Ollama)
decision = scorer.score_from_completion("2]")
print(f"Selected: {decision.selected_candidate.label} (Confidence: {decision.confidence:.2%}, Margin: {decision.margin:.3f})")
```

### 4. Fine-Tune with Tree Loss & KL Anchors
When tuning compact local models (e.g., Qwen 0.6B / 4B) on decision routing datasets:
```python
from cohezion.decision.llm_as_jev import TreeFactorizedListwiseLoss

loss_fn = TreeFactorizedListwiseLoss(reg_lambda=1.0, top_k_tail_approx=64)
loss_dict = loss_fn.compute_loss(gold_logits, ref_logits, gold_tokens, legal_token_sets)
loss = loss_dict["loss"]
```

## VERSION
v0.1

## SEE ALSO
- `STATELESS_LANGUAGE_AGENT_PRIME.md`
- `AUTOHARNESS_PRIME.md`
- `UNIFIED_HYBRID_ROUTER_PRIME.md`
