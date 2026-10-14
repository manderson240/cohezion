# CASMI26 Spectral & Contrastive Head

```python
import numpy as np

def continuous_tanimoto_similarity(pred_probs, candidate_bits):
    """
    Compute continuous Tanimoto similarity between predicted probabilities
    and a binary candidate fingerprint.

    Parameters
    ----------
    pred_probs : np.ndarray
        Array of predicted probabilities, shape (n_features,).
    candidate_bits : np.ndarray
        Binary candidate fingerprint, shape (n_features,).

    Returns
    -------
    float
        Continuous Tanimoto similarity.
    """
    pred_probs = np.asarray(pred_probs, dtype=float)
    candidate_bits = np.asarray(candidate_bits, dtype=float)

    intersection = np.sum(pred_probs * candidate_bits)
    sum_pred = np.sum(pred_probs)
    sum_cand = np.sum(candidate_bits)

    denominator = sum_pred + sum_cand - intersection + 1e-7
    return intersection / denominator
```
We need answer user asks: "In Enveda CASMI26 Molecule ID from Mass Spectra (Top-20 MRR on canonical InChIKey14), formulate a Python function `continuous_tanimoto_similarity(pred_probs, candidate_bits)` calculating exact intersection / (sum(p) + sum(c) - intersection + 1e-7) with NumPy. Enclose valid Python code in ```python ```."

We need provide code. Need understand context maybe continuous Tanimoto similarity for predicted probabilities and candidate bits. Need function with NumPy. Need exact intersection / (sum(p) + sum(c) - intersection + 1e-7). Need likely pred_probs array of floats probabilities, candidate_bits binary array. Intersection = sum(pred_probs * candidate_bits) maybe exact intersection? Continuous Tanimoto: sum(min(p,c))? If candidate bits binary, min(p,c) = p*c for c in {0,1}. So intersection = np.sum(pred_probs * candidate_bits). sum(p)=np.sum(pred_probs), sum(c)=np.sum(candidate_bits). denominator = sum(p)+sum(c)-intersection+1e-7. Return intersection/denominator. Need maybe handle shape. Provide code.

Need maybe include import numpy as np. Function.

Let's craft concise. Ensure valid Python code intriple backticks.
