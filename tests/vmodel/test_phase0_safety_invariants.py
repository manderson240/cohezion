"""SR1 acceptance test — Phase 0 safety invariants.

V-Model right-side test for the System Requirements:
  SR1.1: All heavy lemonade models have bounded ctx_size (N3 invariant).
  SR1.2: max_loaded_models=1 in lemonade config (Strix Halo OOM guard).
  SR1.3: ResourceGuard.can_load_model rejects when RAM < floor.
  SR1.4: ResourceGuard.can_load_model accepts on the live system with >16GB free.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cohezion.inference.oom_guard import verify_all_bounded
from cohezion.reliability.resource_guard import ResourceGuard


LEMONADE_CONFIG = Path.home() / ".cache" / "lemonade" / "config.json"


class TestSR1SafetyInvariants:
    """SR1: the safety floor that must hold before any compound-loop work."""

    def test_sr1_1_all_heavy_models_have_bounded_ctx(self):
        """N3 invariant: no heavy model with ctx_size=0 on the omni router."""
        ok, violations = verify_all_bounded()
        assert ok, f"ctx_size hazards: {violations}"

    def test_sr1_2_max_loaded_models_is_one(self):
        """Strix Halo concurrent-load OOM guard (GCVM_L2 protection fault)."""
        if not LEMONADE_CONFIG.exists():
            pytest.skip("lemonade config not found")
        config = json.loads(LEMONADE_CONFIG.read_text())
        assert config.get("max_loaded_models") == 1, (
            f"max_loaded_models={config.get('max_loaded_models')} — must be 1 to prevent "
            f"Strix Halo GCVM_L2_PROTECTION_FAULT on concurrent JIT compile"
        )

    def test_sr1_3_can_load_model_rejects_below_floor(self):
        guard = ResourceGuard(min_ram_available_mb=16384)
        from cohezion.reliability.resource_guard import SystemVitals
        from unittest.mock import patch

        vitals = SystemVitals(cpu_load_1m=5.0, ram_available_mb=4000, ram_percent=85.0, swap_used_mb=0)
        with patch.object(guard, "get_vitals", return_value=vitals):
            ok, reason = guard.can_load_model(estimated_mb=100)
        assert not ok
        assert "floor" in reason.lower()

    def test_sr1_4_can_load_model_accepts_live_system(self):
        """On the live Strix Halo with >16GB free, a 5GB model is safe to load."""
        guard = ResourceGuard()
        ok, reason = guard.can_load_model(estimated_mb=5000)
        assert ok, f"Live system rejected 5GB load: {reason}"
