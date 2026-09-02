"""Hardware-fit pricing for Hub models via ``hf-mem`` (huggingface-skills).

Gate 1 of the ``local-model-hardware-fit-triage`` skill: settle "can this run
here?" from metadata alone. ``hf-mem`` reads the safetensors / GGUF headers
with HTTP range requests and prices weights + KV cache — nothing is
downloaded, nothing is loaded. KV is priced because the 2026-08-31 freeze was
a load whose KV reservation nobody had priced.

Stdlib-only at import time (``psutil`` + the N3 floor are imported lazily in
``default_fit_budget_bytes``) so callers that only need ``FitEstimate`` pull
in nothing heavy.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import shutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)

# The working quant priced for GGUF repos (fit-triage: "Q4 max params ≈ RAM × 2").
# Token-bounded so "IQ4_K_M" and "Q4_K_M_XL" (different quants) do not match.
_PREFERRED_QUANT_RE = re.compile(r"(?<![a-z0-9])q4_k_m(?![a-z0-9_])", re.IGNORECASE)
# Context the KV cache is priced at — the ctx cap the :13305 router serves models with.
FIT_MAX_MODEL_LEN = 16384
HF_MEM_TIMEOUT_S = 60.0
# Pinned: an unpinned `uvx hf-mem` whose JSON shape drifts would turn every candidate into
# fit_unknown — a silent zero. Bump deliberately and re-run the live smoke.
HF_MEM_SPEC = "hf-mem==0.5.5"


def _size(value: Any) -> int | None:
    """A positive byte count, or None for anything else (null, bool, str, ≤0)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    return int(value)


@dataclass(frozen=True)
class FitEstimate:
    """Bytes a candidate needs to serve: weights + KV cache at ``FIT_MAX_MODEL_LEN``."""

    model_id: str
    filename: str  # the GGUF file priced; "" for safetensors repos
    weights_bytes: int
    kv_bytes: int

    @property
    def total_bytes(self) -> int:
        return self.weights_bytes + self.kv_bytes


FitEstimator = Callable[[str], Awaitable["FitEstimate | None"]]


def parse_hf_mem_output(payload: dict[str, Any]) -> FitEstimate | None:
    """Parse ``hf-mem --json-output`` (``--experimental`` form).

    Safetensors repos give scalar ``memory``/``kv_cache``; GGUF repos give
    per-file dicts (``total_memory`` null). For GGUF the gate prices the
    working quant (``Q4_K_M``), falling back to the smallest file. Entries
    that are null / bool / non-numeric / ≤0 are ignored, never raised on.
    """
    model_id = str(payload.get("model_id", ""))
    memory = payload.get("memory")
    kv = payload.get("kv_cache")
    scalar = _size(memory)
    if scalar is not None:
        return FitEstimate(model_id, "", scalar, _size(kv) or 0)
    if isinstance(memory, dict):
        kv_map = kv if isinstance(kv, dict) else {}
        sized = {f: s for f, v in memory.items() if (s := _size(v)) is not None}
        if not sized:
            return None
        preferred = [f for f in sized if _PREFERRED_QUANT_RE.search(f)]
        fname = preferred[0] if preferred else min(sized, key=lambda f: sized[f])
        return FitEstimate(model_id, fname, sized[fname], _size(kv_map.get(fname)) or 0)
    return None


async def hf_mem_estimate(
    model_id: str, *, max_model_len: int = FIT_MAX_MODEL_LEN
) -> FitEstimate | None:
    """Price ``model_id`` with ``uvx hf-mem`` (Hub HTTP range reads; no download, no load).

    Returns None when hf-mem is unavailable, times out, fails, or emits no
    parseable JSON — callers must treat None as "cannot price", not "fits".
    """
    uvx = shutil.which("uvx")
    if uvx is None:
        logger.warning("hf-mem unavailable: uvx not on PATH")
        return None
    argv = [
        uvx,
        "--from",
        HF_MEM_SPEC,
        "hf-mem",
        "--model-id",
        model_id,
        "--experimental",
        "--max-model-len",
        str(max_model_len),
        "--json-output",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    except OSError as e:
        logger.warning("hf-mem spawn failed for %s: %s", model_id, e)
        return None
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=HF_MEM_TIMEOUT_S)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):  # may have exited between checks
            proc.kill()
            await proc.wait()  # reap — a killed-but-unwaited child is a zombie
        logger.warning("hf-mem timed out (%.0fs) for %s", HF_MEM_TIMEOUT_S, model_id)
        return None
    if proc.returncode != 0:
        logger.warning(
            "hf-mem rc=%s for %s: %s",
            proc.returncode,
            model_id,
            err.decode(errors="replace")[-300:],
        )
        return None
    for line in reversed(out.decode(errors="replace").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return parse_hf_mem_output(json.loads(line))
            except (TypeError, ValueError):  # ValueError covers JSONDecodeError
                logger.warning("hf-mem emitted an unparseable payload for %s", model_id)
                return None
    return None


def default_fit_budget_bytes() -> int:
    """Fit-triage Gate 1: ``available RAM − N3 floor`` (the 16 GB line between working and frozen)."""
    import psutil

    from cohezion.core.resource_management.session_monitor import N3_FLOOR_GB

    return max(0, int(psutil.virtual_memory().available - N3_FLOOR_GB * 2**30))
