"""Training-free overthinking penalty for quantized reasoning tiers.

Motivated by arXiv:2606.00206 ("Quantized Reasoning Models Think They Need to Think Longer, but They
Do Not"): post-training quantization (our GGUF Q4/Q8 reasoning models) corrupts the token distribution,
so at high-entropy positions quantized models over-sample *overthinking markers* ("wait", "but",
"alternatively"), producing longer, less-accurate chains-of-thought. A **logit penalty** on those
markers cuts CoT length 12-23% and overthinking errors up to 58% while preserving/improving accuracy.

`:13305` (llama.cpp OpenAI-compat) accepts `logit_bias` (verified live 2026-07-22), so this is wireable
at $0 with no retrain. This module builds the `logit_bias` map; wiring it into the reasoning tier of
`make_local_execute_fn` / `build_reasoning_orchestrator`, plus the per-model A/B on Qwen3.6-35B, is the
follow-on spike (needs the model's tokenizer + a reasoning benchmark).

The token-id lookup is injected (`token_ids_for`) so this stays tokenizer-agnostic and unit-testable.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable


# The paper's curated overthinking markers (base forms; expanded to tokenizer variants below).
DEFAULT_OVERTHINKING_MARKERS: tuple[str, ...] = (
    "wait",
    "but",
    "alternatively",
    "however",
    "actually",
    "hmm",
    "although",
)


def marker_variants(markers: Iterable[str]) -> list[str]:
    """Expand each base marker into the surface forms a BPE tokenizer actually emits.

    A word mid-sentence is usually tokenized WITH a leading space (" wait"), and sentence-initial
    with a capital (" Wait"/"Wait"). Penalizing only the bare lowercase form misses most real hits —
    this expansion is the whole reason a naive `{token('wait'): -3}` under-performs.
    """
    out: list[str] = []
    seen: set[str] = set()
    for m in markers:
        m = m.strip()
        if not m:
            continue
        for form in (m, " " + m, m.capitalize(), " " + m.capitalize()):
            if form not in seen:
                seen.add(form)
                out.append(form)
    return out


def overthinking_logit_bias(
    token_ids_for: Callable[[str], list[int]],
    markers: Iterable[str] | None = None,
    penalty: float = -3.0,
) -> dict[int, float]:
    """Build a `logit_bias` map {token_id: penalty} for overthinking-marker tokens.

    Parameters
    ----------
    token_ids_for : callable(str) -> list[int]
        Model-specific tokenizer lookup: variant string -> its token id(s). Only single-token
        variants are penalized (a marker that tokenizes to >1 token is skipped — biasing only the
        first sub-token would penalize unrelated continuations).
    markers : iterable of str, optional
        Base markers; defaults to DEFAULT_OVERTHINKING_MARKERS.
    penalty : float
        Logit bias applied to each marker token (negative discourages). Default -3.0.

    Returns a {token_id: penalty} dict ready to pass as OpenAI `logit_bias`.
    """
    base = DEFAULT_OVERTHINKING_MARKERS if markers is None else tuple(markers)
    bias: dict[int, float] = {}
    for form in marker_variants(base):
        ids = token_ids_for(form)
        if len(ids) == 1:  # single-token markers only (see docstring)
            bias[ids[0]] = penalty
    return bias
