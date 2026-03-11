"""Tests for Type-Safe Zero-Copy Validator (Story 1-0-9)."""

from __future__ import annotations

import struct

import pytest

from cohezion.core.zero_copy_validator import (
    ChecksumValidationError,
    SHMBuffer,
    TypeMismatchError,
    ZeroCopyValidator,
)


class TestZeroCopyValidator:
    def test_write_and_read_roundtrip(self):
        validator = ZeroCopyValidator()
        state = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.1, 0.2, 0.3]
        buf = validator.write(state)
        result = validator.validate_and_read(buf)
        for a, b in zip(state, result):
            assert abs(a - b) < 1e-9

    def test_wrong_dtype_rejected(self):
        data = struct.pack("12f", *([1.0] * 12))  # float32 not float64
        buf = SHMBuffer(data=data, declared_dtype="float32", declared_dim=12)
        validator = ZeroCopyValidator()
        with pytest.raises(TypeMismatchError, match="Expected float64"):
            validator.validate_and_read(buf)

    def test_size_mismatch_rejected(self):
        validator = ZeroCopyValidator()
        # Claim 12 dims but only provide 8 dims of data
        data = struct.pack("8d", *([1.0] * 8))
        buf = SHMBuffer(data=data, declared_dtype="float64", declared_dim=12)
        with pytest.raises(TypeMismatchError, match="Buffer size"):
            validator.validate_and_read(buf)

    def test_checksum_failure_falls_back_to_snapshot(self):
        validator = ZeroCopyValidator()
        # Write a good snapshot first
        state = [0.5] * 12
        good_buf = validator.write(state)
        validator.validate_and_read(good_buf)  # populates snapshot

        # Now corrupt the buffer's declared checksum
        corrupted = SHMBuffer(
            data=good_buf.data,
            declared_dtype="float64",
            declared_dim=12,
            checksum="deadbeefdeadbeef",
        )
        result = validator.validate_and_read(corrupted)
        # Returns snapshot values
        for v in result:
            assert abs(v - 0.5) < 1e-9

    def test_checksum_failure_no_snapshot_raises(self):
        validator = ZeroCopyValidator()
        state = [1.0] * 12
        buf = validator.write(state)
        buf.checksum = "wrong_checksum_!!!!"
        with pytest.raises(ChecksumValidationError):
            validator.validate_and_read(buf)

    def test_corruption_events_logged(self):
        validator = ZeroCopyValidator()
        # First write good data to create snapshot
        state = [0.1] * 12
        good = validator.write(state)
        validator.validate_and_read(good)

        # Corrupt
        corrupted = SHMBuffer(
            data=good.data, declared_dtype="float64", declared_dim=12, checksum="badhash"
        )
        validator.validate_and_read(corrupted)
        assert len(validator.corruption_events()) == 1
