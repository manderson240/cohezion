"""Platform test isolation: never read the real GPU lease lock on the box."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_gpu_lease(tmp_path, monkeypatch):
    # GateConfig reads COHEZION_GPU_LEASE_PATH at construction. Without this, a live
    # lease held on the box would turn unrelated gate/proxy tests red.
    monkeypatch.setenv("COHEZION_GPU_LEASE_PATH", str(tmp_path / "gpu-lease.lock"))
    return tmp_path / "gpu-lease.lock"
