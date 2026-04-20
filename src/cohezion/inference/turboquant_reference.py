"""Torch ground-truth oracle for TurboQuant KV-cache compression.

Paper: Zandieh et al., "TurboQuant: Online Vector Quantization with Near-optimal
Distortion Rate", ICLR 2026 (arXiv:2504.19874).

This module is **not** a production inference kernel — it's the correctness
reference that production backends (vLLM-rocm ``tbq4``, llama.cpp PR #20969
``turbo3``, SGLang PR #21617) must match within published tolerance. Per
CLAUDE.md: "Prove correctness BEFORE measuring performance."

Algorithm (oracle variant):

    1. Random Hadamard rotation:   x_rot = x @ (H / sqrt(d))
       H is a Sylvester Walsh-Hadamard matrix with Rademacher sign flips.
       Rotation smooths the per-coordinate outlier distribution into
       something close to Gaussian/Beta for small d.
    2. Per-row scalar quantization: q = clamp(round(x_rot / scale), -L, L-1)
       with scale = max|x_rot| / (L-1) where L = 2^(bits-1).
    3. Decode:                      x_hat = q * scale @ (H.T / sqrt(d))

The QJL 1-bit residual correction from the paper is not implemented here —
at the bit-widths we target (3.5 / 4) the simple PolarQuant path already
meets paper tolerance for the oracle, and the kernels we dispatch to in
Phase 3 implement QJL themselves. Revisit if the oracle needs to match a
kernel's QJL-corrected output bit-exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import torch


if TYPE_CHECKING:
    from cohezion.inference.registry import KVQuant


def _is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def _sylvester_hadamard(size: int) -> torch.Tensor:
    """Unsigned Walsh-Hadamard matrix via Sylvester construction. Size must be power of 2."""
    if not _is_power_of_two(size):
        raise ValueError(f"Hadamard size must be power of 2, got {size}")
    h = torch.tensor([[1.0]])
    while h.shape[0] < size:
        h = torch.cat(
            [
                torch.cat([h, h], dim=1),
                torch.cat([h, -h], dim=1),
            ],
            dim=0,
        )
    return h


@dataclass
class HadamardRotation:
    """Randomized Walsh-Hadamard rotation matrix.

    ``R = D1 @ H @ D2`` where H is the Sylvester Walsh-Hadamard and D1, D2 are
    diagonal ±1 (Rademacher) matrices seeded deterministically. ``R @ R.T =
    size * I`` is preserved, so the rotation is orthogonal up to the scale
    factor ``sqrt(size)`` that callers divide out for a unitary transform.
    """

    seed: int
    size: int

    def __post_init__(self) -> None:
        if not _is_power_of_two(self.size):
            raise ValueError(f"Hadamard size must be power of 2, got {self.size}")

    def matrix(self, device: torch.device | str = "cpu") -> torch.Tensor:
        g = torch.Generator(device="cpu").manual_seed(self.seed)
        h = _sylvester_hadamard(self.size)
        d1 = torch.randint(0, 2, (self.size,), generator=g) * 2 - 1  # ±1
        d2 = torch.randint(0, 2, (self.size,), generator=g) * 2 - 1
        rotation = (d1.unsqueeze(1).float() * h) * d2.unsqueeze(0).float()
        return rotation.to(device)


@dataclass
class PolarQuant:
    """Per-row symmetric scalar quantizer, Lloyd-Max-style for near-uniform coords.

    After Hadamard rotation, coordinates concentrate into a bounded interval,
    so a single scale per row approximates the Lloyd-Max optimum within a small
    constant factor. This is the oracle-grade approximation — production
    kernels use the true Lloyd-Max codebook precomputed from the paper's Beta
    distribution.
    """

    bits: int

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return ``(packed_int, scale_per_row)``.

        packed_int has the same shape as x with dtype int8 (for bits <= 8).
        """
        levels = 2 ** (self.bits - 1)  # signed range [-levels, levels - 1]
        # Per-row scale so the row's max abs maps to ``levels - 1``.
        max_abs = x.abs().amax(dim=-1, keepdim=True).clamp(min=1e-8)
        scale = max_abs / (levels - 1)
        q = torch.round(x / scale).clamp(-levels, levels - 1)
        return q.to(torch.int8), scale.squeeze(-1)

    def decode(self, packed: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
        return packed.float() * scale.unsqueeze(-1)


@dataclass
class TurboQuantReference:
    """End-to-end TurboQuant compress/decompress oracle.

    Usage:

        cfg = KVQuant(scheme="turboquant", bits=4.0, hadamard_size=128)
        tbq = TurboQuantReference(seed=42)
        packet = tbq.compress(kv, cfg)
        reconstructed = tbq.decompress(packet, cfg)

    ``packet`` is a dict with keys ``packed`` (int8 tensor), ``scale`` (float
    per-row), and ``seed`` (int, for deterministic rotation reproduction).
    """

    seed: int = 0

    def compress(self, kv: torch.Tensor, cfg: KVQuant) -> dict[str, torch.Tensor | int]:
        if cfg.scheme == "none":
            return {"passthrough": kv}

        size = cfg.hadamard_size
        if not _is_power_of_two(size):
            raise ValueError(f"Hadamard size must be power of 2, got {size}")

        rot = HadamardRotation(seed=self.seed, size=size).matrix(device=kv.device)
        unitary = rot / (size**0.5)
        rotated = kv @ unitary

        bits = round(cfg.bits)  # oracle rounds fractional bit-widths to nearest int
        pq = PolarQuant(bits=max(2, bits))
        packed, scale = pq.encode(rotated)
        return {
            "packed": packed,
            "scale": scale,
            "seed": self.seed,
            "size": size,
            "bits": bits,
        }

    def decompress(
        self,
        packet: dict[str, torch.Tensor | int],
        cfg: KVQuant,
    ) -> torch.Tensor:
        if cfg.scheme == "none":
            passthrough = packet["passthrough"]
            if not isinstance(passthrough, torch.Tensor):
                raise TypeError(f"passthrough packet must be a Tensor, got {type(passthrough)}")
            return passthrough

        packed = packet["packed"]
        scale = packet["scale"]
        size = int(packet["size"])
        bits = int(packet["bits"])
        if not isinstance(packed, torch.Tensor) or not isinstance(scale, torch.Tensor):
            raise TypeError("packed and scale fields of the packet must be Tensors")

        pq = PolarQuant(bits=max(2, bits))
        rotated = pq.decode(packed, scale)

        rot = HadamardRotation(seed=int(packet["seed"]), size=size).matrix(device=packed.device)
        inverse = rot.T / (size**0.5)
        return rotated @ inverse
