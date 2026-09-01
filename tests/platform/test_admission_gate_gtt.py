"""Gate v2 GTT-headroom invariants for the admission gate.

GTT is uncgroupable and unreclaimable — the kernel OOM killer never sees it (the
08-15/08-31 root cause). The RAM floor alone cannot bound it: MemAvailable and GTT
usage diverge because GTT pages are lent, not accounted. The gate therefore refuses
UMA-tier loads that would push GTT past GTT_HEADROOM_FRACTION of the ceiling.

Discriminating: on the pre-v2 gate every test asserting a GTT refusal fails
(the gate had no GTT awareness at all).
"""

from __future__ import annotations

from unittest.mock import patch

from cohezion.platform.admission_gate import (
    GTT_HEADROOM_FRACTION,
    AdmissionGate,
    GateConfig,
    read_gtt_usage_gb,
)


CFG = GateConfig(floor_gb=16.0, enforce=True)


def _gate(**over: object) -> AdmissionGate:
    kwargs: dict[str, object] = {
        "config": CFG,
        "read_available_gb": lambda: 60.0,  # far above the floor — isolate the GTT check
        "read_resident": lambda: [],
    }
    kwargs.update(over)
    return AdmissionGate(**kwargs)  # type: ignore[arg-type]


class TestGTTHeadroom:
    def test_refuses_gpu_load_when_gtt_nearly_full(self):
        gate = _gate(read_gtt=lambda: (80.0, 96.0))
        with patch("cohezion.platform.admission_gate.check_oom_risk") as risk:
            risk.return_value.safe = True
            risk.return_value.footprint_gb = 20.0
            decision = gate.decide("Qwen3.6-35B-A3B-GGUF")
        # 80 + 20 = 100 > 0.85 × 96 = 81.6 → refuse.
        assert decision.allow is False
        assert "GTT" in decision.reason

    def test_allows_gpu_load_with_gtt_headroom(self):
        gate = _gate(read_gtt=lambda: (30.0, 96.0))
        with patch("cohezion.platform.admission_gate.check_oom_risk") as risk:
            risk.return_value.safe = True
            risk.return_value.footprint_gb = 20.0
            risk.return_value.reason = "within memory budget"
            decision = gate.decide("Qwen3.6-35B-A3B-GGUF")
        assert decision.allow is True

    def test_npu_model_not_gtt_gated(self):
        # FLM/NPU loads do not draw GTT — a full GTT must not block them.
        gate = _gate(read_gtt=lambda: (90.0, 96.0))
        with patch("cohezion.platform.admission_gate.check_oom_risk") as risk:
            risk.return_value.safe = True
            risk.return_value.footprint_gb = 1.3
            risk.return_value.reason = "ok"
            decision = gate.decide("llama3.2-1b-FLM")
        assert decision.allow is True

    def test_gtt_unreadable_fails_open(self):
        # Same doctrine as the blind-memory path: unreadable telemetry must not
        # take the fleet down by itself; it allows, loudly.
        gate = _gate(read_gtt=lambda: None)
        with patch("cohezion.platform.admission_gate.check_oom_risk") as risk:
            risk.return_value.safe = True
            risk.return_value.footprint_gb = 20.0
            risk.return_value.reason = "ok"
            decision = gate.decide("Qwen3.6-35B-A3B-GGUF")
        assert decision.allow is True

    def test_headroom_fraction_is_conservative(self):
        assert 0.5 <= GTT_HEADROOM_FRACTION <= 0.9

    def test_budget_bounded_by_mem_total_when_ceiling_exceeds_ram(self):
        # rv-gate-v2 H1: live pre-reboot state is a 128 GiB GTT ceiling on a 122.8 GiB
        # box — a raw fraction-of-ceiling budget (108.8) is unreachable, so the check
        # is dormant. Bounding by MemTotal makes it fire: budget = 0.85 × 122.8 = 104.4;
        # used 90 + load 15 = 105 must REFUSE (a ceiling-based budget of 108.8 allows).
        gate = _gate(read_gtt=lambda: (90.0, 128.0))
        with (
            patch("cohezion.platform.admission_gate._mem_total_gb", return_value=122.8),
            patch("cohezion.platform.admission_gate.check_oom_risk") as risk,
        ):
            risk.return_value.safe = True
            risk.return_value.footprint_gb = 15.0
            decision = gate.decide("Qwen3.6-35B-A3B-GGUF")
        assert decision.allow is False
        assert "GTT" in decision.reason

    def test_flm_suffix_model_not_gtt_gated(self):
        # rv-gate-v2 M5: only 3 FLM models are in MODEL_TIER; the other catalog FLM
        # entries must still skip the GTT check (FLM draws no GTT) via the -FLM suffix.
        gate = _gate(read_gtt=lambda: (95.0, 96.0))
        with patch("cohezion.platform.admission_gate.check_oom_risk") as risk:
            risk.return_value.safe = True
            risk.return_value.footprint_gb = 4.0
            risk.return_value.reason = "ok"
            decision = gate.decide("qwen3vl-it-4b-FLM")
        assert decision.allow is True


class TestReadGttUsage:
    def test_returns_pair_or_none(self):
        got = read_gtt_usage_gb()
        assert got is None or (
            isinstance(got, tuple) and len(got) == 2 and got[1] > 0.0 and got[0] >= 0.0
        )
