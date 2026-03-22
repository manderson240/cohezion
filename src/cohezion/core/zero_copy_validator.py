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
    declared_dtype: str  # "float64" expected
    declared_dim: int
    checksum: str = ""

    def compute_checksum(self) -> str:
        return hashlib.sha256(self.data).hexdigest()[:16]


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

    def __init__(self) -> None:
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

        expected_bytes = buf.declared_dim * FLOAT64_BYTES
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

            values = list(struct.unpack(f"{MANIFOLD_DIM}d", self._last_good_snapshot))
            return values

        # Successfully validated — update snapshot
        self._last_good_snapshot = buf.data
        count = buf.declared_dim
        return list(struct.unpack(f"{count}d", buf.data))

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
