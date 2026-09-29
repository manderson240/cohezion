"""KV-cache budget pre-flight gate — a deterministic OOM guard for model loads.

Overnight finding A9 turned into code. The 2026-06-09 OOM crasher (harness note **N3**) was a
heavy model loaded at ``ctx_size=0`` (full context) → unbounded KV cache → the box hung until a
cold boot. N3 calls the crash "non-deterministic — depends on FREE MEMORY at load time." It does
not have to be: the KV-cache footprint is an exact function of the model shape, context, batch,
and cache dtype, so a load can be **refused before it is attempted**.

Elegantly simple, and pure: no network, no fleet mutation, stdlib only. A loader calls
:func:`preflight` with the live free memory + the model's shape and gets back an allow/deny plus a
diagnostic dict. The three "make it fit" levers all live in the same formula: ``seq_len`` (ctx),
``batch`` (``-np``), and ``cache_dtype`` (q8_0/q4_0 halve/quarter the KV).

Formula (GQA):  ``KV_bytes = 2 · num_layers · num_kv_heads · head_dim · seq_len · batch · bytes``
Verified against published Llama-3.1-8B numbers: FP16 ≈ 4 GiB @32k, ≈ 16 GiB @128k.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple


# Bytes per KV element by llama.cpp cache dtype. FP16 is the default (2 B); q8_0/q4_0 are the
# standard KV-cache quantization levels (finding A3) — they halve / quarter the footprint.
_CACHE_DTYPE_BYTES: dict[str, float] = {
    "fp16": 2.0,
    "f16": 2.0,
    "q8_0": 1.0,
    "q8": 1.0,
    "q4_0": 0.5,
    "q4": 0.5,
}


def kv_cache_bytes(
    *,
    num_layers: int,
    num_kv_heads: int,
    head_dim: int,
    seq_len: int,
    batch: int = 1,
    cache_dtype: str = "fp16",
    mla_latent_dim: int | None = None,
) -> int:
    """Return the KV-cache footprint in bytes for one loaded model at ``seq_len`` context.

    GQA-aware: pass ``num_kv_heads`` (the K/V head count), not the query-head count — that is the
    architectural saving GQA buys. ``cache_dtype`` is the llama.cpp KV cache type; unknown values
    raise ``KeyError`` (fail loud rather than silently mis-budget).

    ``mla_latent_dim`` (merged from the retired kv_cache_calculator.py): DeepSeek-style
    multi-head latent attention caches one ``latent_dim`` vector per layer per token instead of
    ``2 · num_kv_heads · head_dim`` — pass the latent dim to budget MLA models (R1/V3).
    """
    if mla_latent_dim is not None:
        return int(num_layers * mla_latent_dim * seq_len * batch * _CACHE_DTYPE_BYTES[cache_dtype])
    return int(
        2 * num_layers * num_kv_heads * head_dim * seq_len * batch * _CACHE_DTYPE_BYTES[cache_dtype]
    )


def preflight(
    *,
    free_bytes: int,
    weight_bytes: int,
    num_layers: int,
    num_kv_heads: int,
    head_dim: int,
    seq_len: int,
    batch: int = 1,
    cache_dtype: str = "fp16",
    buffer_bytes: int,
    mla_latent_dim: int | None = None,
) -> tuple[bool, dict[str, int]]:
    """Decide whether loading a model fits in memory, deterministically.

    ``ok`` is True iff ``weight_bytes + kv_bytes + buffer_bytes <= free_bytes``. ``buffer_bytes`` is
    the safety headroom the caller reserves (fragmentation, other tensors, the OS). Returns
    ``(ok, info)`` where ``info`` is a full byte-level diagnostic — including a signed
    ``headroom_bytes`` (negative = by how much it would overflow) so callers/logs can explain the
    decision rather than just see a bool.
    """
    kv_bytes = kv_cache_bytes(
        num_layers=num_layers,
        num_kv_heads=num_kv_heads,
        head_dim=head_dim,
        seq_len=seq_len,
        batch=batch,
        cache_dtype=cache_dtype,
        mla_latent_dim=mla_latent_dim,
    )
    total_bytes = weight_bytes + kv_bytes
    headroom_bytes = free_bytes - total_bytes - buffer_bytes
    info = {
        "kv_bytes": kv_bytes,
        "weight_bytes": weight_bytes,
        "total_bytes": total_bytes,
        "free_bytes": free_bytes,
        "buffer_bytes": buffer_bytes,
        "headroom_bytes": headroom_bytes,
    }
    return headroom_bytes >= 0, info


# ── Architecture-aware KV (from real GGUF headers) ──────────────────────────────────────────
# The GQA formula above assumes EVERY layer caches K/V for the whole context. That is wrong for
# most current families: hybrid Gated-DeltaNet (qwen3next/qwen35*) caches KV on 1 layer in
# ``full_attention_interval``; Mamba2/conv hybrids (nemotron_h_moe, lfm2moe) only on layers with
# a non-zero ``head_count_kv``; gemma4 caps its sliding-window layers at ``sliding_window``
# tokens; MLA (deepseek2) stores one latent per layer. Measured 2026-09-29: Qwen3-Coder-Next
# 0.21 GB @32k (q4_0) vs 2.5 GB under the all-GQA assumption. Recurrent layers additionally hold
# a FIXED per-sequence state (fp32 ``ssm.inner_size * ssm.state_size``), independent of context.

_PROFILES_PATH = Path(__file__).parent / "gguf_kv_profiles.json"
_DEFAULT_FULL_ATTENTION_INTERVAL = 4  # qwen3next headers omit the key; the family is 3:1


class KVProfile(NamedTuple):
    """Per-sequence KV shape: elements/token (global, SWA), SWA window, fixed state bytes."""

    global_elems_per_token: int
    swa_elems_per_token: int
    swa_window: int
    fixed_state_bytes: int


def kv_profile_from_gguf_meta(meta: dict) -> KVProfile:
    """Derive a :class:`KVProfile` from (trimmed) GGUF header metadata. Pure, no I/O.

    Unknown or unverified architectures fall through to the conservative all-layers-full-GQA
    upper bound rather than raising — an over-estimate refuses a load, an under-estimate OOMs.
    """
    a = meta["general.architecture"]

    def g(*keys: str):
        return next((meta[f"{a}.{k}"] for k in keys if f"{a}.{k}" in meta), None)

    layers = g("block_count")
    kvh = g("attention.head_count_kv", "head_count_kv")
    heads = g("attention.head_count", "head_count")
    emb = g("embedding_length")
    head_dim = (emb // heads) if emb and heads else 0
    key_len = g("attention.key_length", "key_length") or head_dim
    val_len = g("attention.value_length", "value_length") or head_dim
    interval = g("full_attention_interval")
    if interval is None and a == "qwen3next":
        interval = _DEFAULT_FULL_ATTENTION_INTERVAL
    per_layer = [kvh] * layers if not isinstance(kvh, list) else list(kvh)
    swa_window, swa_elems = 0, 0
    pattern = g("attention.sliding_window_pattern")

    if g("attention.kv_lora_rank"):  # MLA: one latent (kv_lora + rope) per layer, no K/V split
        return KVProfile(layers * key_len, 0, 0, 0)
    if interval:  # hybrid GDN: only every ``interval``-th layer holds KV
        attn = [i for i in range(layers) if (i + 1) % interval == 0]
    else:
        attn = [i for i in range(layers) if per_layer[i]]
    per_token = sum(per_layer[i] * (key_len + val_len) for i in attn)
    if isinstance(pattern, list):  # gemma4: True = sliding-window layer
        swa_idx = {i for i in attn if i < len(pattern) and pattern[i]}
        swa_elems = sum(per_layer[i] * (key_len + val_len) for i in swa_idx)
        per_token -= swa_elems
        swa_window = g("attention.sliding_window") or 0
    inner, state = g("ssm.inner_size"), g("ssm.state_size")
    fixed = (layers - len(attn)) * inner * state * 4 if inner and state else 0
    return KVProfile(per_token, swa_elems, swa_window, fixed)


def kv_bytes_from_profile(
    p: KVProfile, *, seq_len: int, batch: int = 1, cache_dtype: str = "q4_0"
) -> int:
    """KV + fixed recurrent state, in bytes, for ``batch`` sequences of ``seq_len`` tokens."""
    elems = p.global_elems_per_token * seq_len + p.swa_elems_per_token * min(seq_len, p.swa_window)
    return int(elems * _CACHE_DTYPE_BYTES[cache_dtype] * batch + p.fixed_state_bytes * batch)


@lru_cache(maxsize=1)
def _profiles() -> dict[str, KVProfile]:
    raw = json.loads(_PROFILES_PATH.read_text())
    return {mid: kv_profile_from_gguf_meta(m) for mid, m in raw.items()}


def profile_for(model_id: str) -> KVProfile | None:
    """Profile for a Lemonade model id, or None when its header was never surveyed."""
    return _profiles().get(model_id)


def ctx_cap_for(
    model_id: str, *, floor: int, budget_bytes: int, hard_max: int = 131072, dtype: str = "q4_0"
) -> int:
    """Largest context (multiple of 1024) whose KV+state fits ``budget_bytes``.

    Unprofiled models return ``floor`` (the caller's existing conservative cap) so behaviour for
    them is unchanged; a profiled model never returns below ``floor``.
    """
    p = profile_for(model_id)
    if p is None or p.global_elems_per_token <= 0:
        return floor
    b = _CACHE_DTYPE_BYTES[dtype]
    swa = p.swa_elems_per_token * p.swa_window * b
    n = int((budget_bytes - p.fixed_state_bytes - swa) / (p.global_elems_per_token * b))
    return max(floor, min(hard_max, n // 1024 * 1024))
