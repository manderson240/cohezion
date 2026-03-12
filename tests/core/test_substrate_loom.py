"""Tests for Substrate Loom Zero-Copy SHM (Story 1.4)."""

from __future__ import annotations

import numpy as np

from cohezion.core.substrate_loom import LoomMode, SubstrateLoom


class TestSubstrateLoom:
    def test_write_and_read_roundtrip(self):
        loom = SubstrateLoom()
        state = np.array([float(i) for i in range(12)])
        loom.write(state)
        result = loom.read()
        np.testing.assert_array_almost_equal(state, result)

    def test_flip_count_increments_on_write(self):
        loom = SubstrateLoom()
        assert loom.flip_count == 0
        loom.write(np.zeros(12))
        loom.write(np.zeros(12))
        assert loom.flip_count == 2

    def test_watchdog_healthy_after_write(self):
        loom = SubstrateLoom()
        loom.write(np.zeros(12))
        assert loom.check_watchdog() is True
        assert loom.mode == LoomMode.ACTIVE

    def test_watchdog_detects_stale_pointer(self):
        loom = SubstrateLoom()
        loom.write(np.zeros(12))
        loom.simulate_rust_crash()
        assert loom.check_watchdog() is False
        assert loom.mode == LoomMode.DEGRADED

    def test_snapshot_preserved_before_crash(self):
        loom = SubstrateLoom()
        state = np.array([0.5] * 12)
        loom.write(state)
        loom.simulate_rust_crash()
        snapshot = loom.recover_from_snapshot()
        assert snapshot is not None
        np.testing.assert_array_almost_equal(snapshot.state, state)

    def test_no_snapshot_before_write(self):
        loom = SubstrateLoom()
        assert loom.recover_from_snapshot() is None

    def test_mode_starts_active(self):
        loom = SubstrateLoom()
        assert loom.mode == LoomMode.ACTIVE
