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
) -> int:
    """Return the KV-cache footprint in bytes for one loaded model at ``seq_len`` context.

    GQA-aware: pass ``num_kv_heads`` (the K/V head count), not the query-head count — that is the
    architectural saving GQA buys. ``cache_dtype`` is the llama.cpp KV cache type; unknown values
    raise ``KeyError`` (fail loud rather than silently mis-budget).
    """
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
