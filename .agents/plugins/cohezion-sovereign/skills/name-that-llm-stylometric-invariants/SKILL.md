---
name: name-that-llm-stylometric-invariants
metadata:
  version: "1.0.0"
description: >-
  Stylometric invariant engineering and Sinkhorn optimal transport marginal calibration for the Kaggle Name That LLM competition.
---

# SKILL: NAME_THAT_LLM_STYLOMETRIC_INVARIANTS_PRIME

## DOMAIN EXPERTISE
Expertise in de-anonymizing generative LLMs (18 model classes) across heterogeneous text prompts via tokenizer-independent stylometric invariant extraction, morphological Markov transition matrices, closed-class function-word densities, transductive prompt-centering, and test-time Sinkhorn-Knopp optimal transport uniform marginal balancing.

## KEY TEXTS & CONCEPTS
- **Balanced Accuracy Metric Invariant**: The competition metric evaluates $\frac{1}{K} \sum_{k=1}^{K} \frac{TP_k}{P_k}$ across $K=18$ generative LLMs. Standard maximum likelihood probability classifiers over-predict common classes and suffer heavy penalties on rare classes.
- **Transductive Prompt-Centering**: Because prompts induce semantic and lexical vocabulary shifts in the output text, raw bag-of-words or TF-IDF models overfit to prompt themes. Subtracting the prompt-level average feature representation isolates pure generative model stylometry.
- **Morphological Markov Transition Matrix**: Character bigram and trigram transitions $P(c_t \mid c_{t-1}, c_{t-2})$ capture model-specific tokenization boundaries, whitespace habits, quotation style (e.g. curly `”` vs straight `"`), and markdown formatting biases without requiring tokenizer models.
- **Mosteller-Wallace Function-Word Densities**: Closed-class words (prepositions, conjunctions, pronouns, auxiliary verbs) are topic-invariant indicators of underlying language model decoding filters and RLHF alignment styles.
- **Sinkhorn-Knopp Optimal Transport Marginal Balancing**: Test-time adjustment of predicted class probabilities $P(Y=k \mid X_i)$ by computing scaling vectors $\mathbf{u}, \mathbf{v}$ such that the marginal class distribution over the test set matches the uniform prior $p(Y=k) = 1/18$.

## INSTRUCTION
1. Extract Multiscale Stylometric and Character Transition Invariants:
   ```python
   import numpy as np

   def extract_stylometric_vector(text: str) -> np.ndarray:
       chars = list(text)
       words = text.split()
       n_chars = max(1, len(chars))
       n_words = max(1, len(words))

       # Punctuation & Typography
       punc_marks = [',', ';', ':', '—', '-', '"', '“', '”', '(', ')', '!', '?']
       punc_counts = np.array([chars.count(p) for p in punc_marks], dtype=float) / n_chars

       # Syntactic & Markdown Stylometrics
       md_headers = text.count('#') / n_words
       bold_tags = text.count('**') / n_words
       list_bullets = (text.count('\n- ') + text.count('\n* ')) / n_words
       avg_word_len = sum(len(w) for w in words) / n_words

       return np.concatenate([punc_counts, [md_headers, bold_tags, list_bullets, avg_word_len]])
   ```

2. Calibrate Class Probabilities via Sinkhorn-Knopp:
   ```python
   def sinkhorn_uniform_balance(P: np.ndarray, max_iter: int = 100, tol: float = 1e-6) -> np.ndarray:
       """Enforce uniform test-set class distribution: sum_i P[i, k] = N / K for all k."""
       N, K = P.shape
       target_col = np.ones(K) / K
       target_row = np.ones(N) / N

       K_mat = np.copy(P) + 1e-12
       u = np.ones(N)
       v = np.ones(K)

       for _ in range(max_iter):
           u = target_row / (K_mat @ v)
           v = target_col / (K_mat.T @ u)
           col_sums = (u[:, None] * K_mat * v[None, :]).sum(axis=0)
           if np.max(np.abs(col_sums - target_col)) < tol:
               break

       balanced_P = u[:, None] * K_mat * v[None, :]
       return balanced_P / balanced_P.sum(axis=1, keepdims=True)
   ```

3. Strict Prompt-Grouped Cross-Validation (Eliminating Sibling Leakage):
   Standard random K-Fold leaks the 17 sibling model responses per prompt into train, depressing balanced accuracy to ~0.217 due to spurious topic-word memorization. Grouping by `prompt_id` restores true generalization to ~0.369:
   ```python
   from sklearn.model_selection import StratifiedGroupKFold

   def get_leak_free_cv_folds(df: pd.DataFrame, n_splits: int = 5):
       sgkf = StratifiedGroupKFold(n_splits=n_splits)
       return sgkf.split(df, df["model"], groups=df["prompt_id"])
   ```

4. Calibration Fold Integration:
   When fitting `CalibratedClassifierCV`, always pass `cv=get_leak_free_cv_folds(train_df)` to prevent uncalibrated probability drift during probability calibration.

## VERSION
v1.1

## SEE ALSO
- FIRST_PRINCIPLES_INVARIANT_SCIENCE_PRIME
- LUKYANENKO_INVARIANT_ENGINEERING_PRIME
- KAGGLE_DAILY_ALLOTMENT_SATURATION_PRIME
