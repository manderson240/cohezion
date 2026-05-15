"""Type-Safe Zero-Copy Hardening (Story 1-0-9, NFR-9, Security).

Validates type-width (Float64, 8 bytes/dimension) at the Rust-Python SHM boundary.
On type mismatch: hard rejection with descriptive error (not a segfault).
On corrupted buffer: checksum validation fails, falls back to last-known-good snapshot.
"""

from __future__ import annotations

import hashlib
import logging
import struct
from dataclasses import dataclass


logger = logging.getLogger(__name__)

FLOAT64_BYTES = 8
MANIFOLD_DIM = 12


class TypeMismatchError(ValueError):
    """Raised when type-width validation fails at the SHM boundary."""


class ChecksumValidationError(RuntimeError):
    """Raised when buffer checksum fails."""


@dataclass
class SHMBuffer:
    """Simulated shared memory buffer with type-width metadata."""

    data: bytes
    declared_dtype: str = "float64"  # "float64" expected
    declared_dim: int = 0  # inferred from data length if 0
    checksum: str = ""
    # Accept 'dtype' as alias for declared_dtype (test interface)
    dtype: str = ""

    def __post_init__(self) -> None:
        # dtype alias: if dtype provided, use it as declared_dtype
        if self.dtype:
            self.declared_dtype = self.dtype
        # Infer declared_dim from data size if not provided
        if self.declared_dim == 0 and self.data:
            self.declared_dim = len(self.data) // FLOAT64_BYTES

    def compute_checksum(self) -> str:
        """Return full SHA-256 hex digest of buffer data."""
        return hashlib.sha256(self.data).hexdigest()


@dataclass
class ValidationReport:
    valid: bool
    reason: str = ""
    fell_back_to_snapshot: bool = False
    corruption_logged: bool = False

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "reason": self.reason,
            "fell_back_to_snapshot": self.fell_back_to_snapshot,
            "corruption_logged": self.corruption_logged,
        }


class ZeroCopyValidator:
    """Validates Float64 type-width and buffer checksum at the Rust-Python boundary."""

    def __init__(self, expected_dim: int = MANIFOLD_DIM) -> None:
        self._expected_dim = expected_dim
        self._last_good_snapshot: bytes | None = None
        self._corruption_events: list[dict] = []

    def validate_and_read(self, buf: SHMBuffer) -> list[float]:
        """Validate buffer and return the 12D state vector.

        Raises TypeMismatchError on dtype/width mismatch.
        Falls back to snapshot on checksum failure.
        """
        # Type-width validation
        if buf.declared_dtype != "float64":
            raise TypeMismatchError(
                f"Expected float64 (8 bytes/dim) but received {buf.declared_dtype!r}. "
                "Hard rejection at SHM boundary to prevent segfault."
            )

        # Use expected_dim (validator-level) or buf.declared_dim (buffer-level)
        dim = buf.declared_dim if buf.declared_dim > 0 else self._expected_dim
        expected_bytes = dim * FLOAT64_BYTES
        if len(buf.data) != expected_bytes:
            raise TypeMismatchError(
                f"Buffer size {len(buf.data)} does not match "
                f"{buf.declared_dim} float64 dimensions ({expected_bytes} bytes expected). "
                "Hard rejection at SHM boundary."
            )

        # Checksum validation
        actual_checksum = buf.compute_checksum()
        if buf.checksum and actual_checksum != buf.checksum:
            self._corruption_events.append(
                {
                    "declared_checksum": buf.checksum,
                    "actual_checksum": actual_checksum,
                    "dim": buf.declared_dim,
                }
            )
            logger.warning("SHM checksum mismatch — falling back to last known-good snapshot")

            if self._last_good_snapshot is None:
                raise ChecksumValidationError("Checksum failed and no snapshot available")

            snap_dim = len(self._last_good_snapshot) // FLOAT64_BYTES
            values = list(struct.unpack(f"{snap_dim}d", self._last_good_snapshot))
            return values

        # Successfully validated — update snapshot
        self._last_good_snapshot = buf.data
        return list(struct.unpack(f"{dim}d", buf.data))

    def write(self, state: list[float]) -> SHMBuffer:
        """Serialize a state vector into an SHM buffer with type-width metadata."""
        data = struct.pack(f"{len(state)}d", *state)
        buf = SHMBuffer(
            data=data,
            declared_dtype="float64",
            declared_dim=len(state),
        )
        buf.checksum = buf.compute_checksum()
        return buf

    def corruption_events(self) -> list[dict]:
        return list(self._corruption_events)
