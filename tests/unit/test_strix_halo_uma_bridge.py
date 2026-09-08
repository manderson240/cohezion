"""Unit tests for Strix Halo Zero-Copy UMA Shared Memory Bridge."""

import numpy as np
import pytest

from cohezion.inference.strix_halo_uma_bridge import (
    POINCARE_DIM,
    StrixHaloUnifiedMemoryBridge,
)


def test_strix_halo_uma_bridge_write_and_read(tmp_path):
    shm_test_file = str(tmp_path / "test_strix_halo_uma.dat")
    bridge = StrixHaloUnifiedMemoryBridge(shm_path=shm_test_file, create=True)

    # Generate synthetic 2048D Poincare coordinate vector
    coords = np.random.normal(0, 0.05, POINCARE_DIM).astype(np.float32)
    seq = 42
    coherence = 0.775
    dirichlet_e = 0.0045

    slot = bridge.write_state(seq, coherence, dirichlet_e, coords)
    assert 0 <= slot < 16

    # Read back zero-copy
    packet = bridge.read_latest_state()
    assert packet is not None
    assert packet.sequence == seq
    assert abs(packet.coherence - coherence) < 1e-5
    assert abs(packet.dirichlet_energy - dirichlet_e) < 1e-5
    assert len(packet.coords) == POINCARE_DIM
    np.testing.assert_allclose(packet.coords, coords, rtol=1e-5)

    bridge.close()
