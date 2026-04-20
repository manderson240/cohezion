"""Spinor coherence → TurboQuant KV-cache axis translator.

Inference runtimes (vLLM-rocm, llama.cpp PR #20969, SGLang PR #21617) accept a
``turboquant_axis`` hint alongside the OpenAI chat payload. The hint lets the
KV-cache quantizer seed its Hadamard rotation from the agent's current SPIN
coherence so rotation-based compression aligns with the physics layer rather
than sampling an independent random seed per call.

This module is the single point where that coherence (a float in [0, 1]) is
translated into the payload field the runtimes parse. Before this module
existed, ``fleet._inject_symmetry_axis`` caught ``ImportError`` silently at
the debug log level — every ``route()`` call ran without axis injection.
See ``.claude/plans/dreamy-jingling-thacker.md`` Phase 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Default 3.5-bit KV quantization per ICLR 2026 (Zandieh et al., arXiv:2504.19874).
# Runtimes that don't implement TurboQuant ignore the field; runtimes that do
# dispatch to ``tbq4`` / ``turbo3`` kernels and derive a Hadamard matrix from
# ``hadamard_seed`` at KV-cache creation time.
_DEFAULT_BITS: float = 3.5
_SEED_SCALE: int = 2**31 - 1  # Map [0, 1] → a deterministic 31-bit seed.


@dataclass
class SymmetryHardwareBridge:
    """Translates agent coherence into a TurboQuant axis payload hint.

    Stateless, safe to share across threads. Instantiate via ``get_symmetry_bridge()``
    so downstream callers see a single instance they can identity-compare if
    they need to (e.g. tests).
    """

    bits: float = _DEFAULT_BITS

    def apply_to_payload(
        self,
        payload: dict[str, Any],
        coherence: float,
    ) -> dict[str, Any]:
        """Return a new payload with ``turboquant_axis`` appended.

        ``coherence`` is clamped into [0, 1] so callers with unnormalized SPIN
        magnitudes (e.g. mid-evolution before normalization) don't produce
        nonsense seeds. The seed is derived deterministically from the clamped
        coherence — same coherence → same seed — so axis alignment is
        reproducible across retries.
        """
        clamped = max(0.0, min(1.0, float(coherence)))
        hadamard_seed = int(clamped * _SEED_SCALE)

        new_payload = dict(payload)  # shallow copy — don't mutate caller's dict
        new_payload["turboquant_axis"] = {
            "coherence": clamped,
            "hadamard_seed": hadamard_seed,
            "bits": self.bits,
        }
        return new_payload


_bridge_singleton: SymmetryHardwareBridge | None = None


def get_symmetry_bridge() -> SymmetryHardwareBridge:
    """Return the module-level singleton bridge instance."""
    global _bridge_singleton
    if _bridge_singleton is None:
        _bridge_singleton = SymmetryHardwareBridge()
    return _bridge_singleton
