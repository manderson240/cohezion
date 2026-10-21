"""The aperture guard rules on backend and GTT, never on a model's name.

Live defect 2026-10-21: with the guard enabled, the admission proxy refused
``Gemma-4-E2B-it-GGUF`` (a ~3 GB model on the CPU backend) because its name ends
in ``-GGUF``. Every triune tier past the NPU got HTTP 503 and was told to go to
cloud. The byte gate behind the guard would have admitted it.
"""

from __future__ import annotations

from unittest.mock import patch

from cohezion.inference.aperture_guard import validate_tier1_request
from cohezion.platform.admission_gate import AdmissionGate, GateConfig


def _gate(resident: list[str] | None = None, available_gb: float = 60.0) -> AdmissionGate:
    return AdmissionGate(
        config=GateConfig(floor_gb=16.0, enforce=True, enforce_aperture_guard=True),
        read_available_gb=lambda: available_gb,
        read_resident=lambda: [{"model_name": n, "checkpoint": ""} for n in (resident or [])],
        read_gtt=lambda: None,
        read_swap=lambda: 0.0,
        read_psi=lambda: 0.0,
    )


_NO_GTT = patch("cohezion.inference.aperture_guard.get_current_gtt_used_bytes", return_value=0)


class TestGuardRulesOnFactsNotNames:
    def test_cpu_gguf_is_not_refused_by_name(self) -> None:
        # The exact refusal seen live. The old name rule returned reroute_tier2.
        with _NO_GTT:
            assert validate_tier1_request("Gemma-4-E2B-it-GGUF") == "allow"
            assert validate_tier1_request("Bonsai-8B-gguf", backend="cpu") == "allow"

    def test_gpu_backend_is_still_refused(self) -> None:
        # The guard's real job survives: a GPU-backend load is refused whatever the name.
        with _NO_GTT:
            assert validate_tier1_request("Qwen3-0.6B-GGUF", backend="vulkan") == "reroute_tier2"
            assert validate_tier1_request("Gemma-4-E2B-it-GGUF", backend="rocm") == "reroute_tier2"

    def test_gtt_saturation_still_refuses_non_npu(self) -> None:
        with patch(
            "cohezion.inference.aperture_guard.get_current_gtt_used_bytes",
            return_value=45 * 1024**3,
        ):
            assert validate_tier1_request("Gemma-4-E2B-it-GGUF") == "reroute_tier2"


class TestGateOrdering:
    def test_resident_model_is_reused_even_on_gpu_saturation(self) -> None:
        # Reuse maps nothing new; the guard must not run before the resident check.
        with patch(
            "cohezion.inference.aperture_guard.get_current_gtt_used_bytes",
            return_value=45 * 1024**3,
        ):
            d = _gate(resident=["Gemma-4-E2B-it-GGUF"]).decide("Gemma-4-E2B-it-GGUF")
        assert d.allow is True
        assert "resident" in d.reason

    def test_small_cpu_gguf_reaches_byte_gate_and_is_admitted(self) -> None:
        with (
            _NO_GTT,
            patch(
                "cohezion.compound.oom_guard._catalog_entry",
                return_value={"id": "Gemma-4-E2B-it-GGUF", "size": 3.1, "recipe": "llamacpp"},
            ),
        ):
            d = _gate(resident=[]).decide("Gemma-4-E2B-it-GGUF")
        assert d.allow is True, d.reason
        assert "aperture" not in d.reason

    def test_memory_refusals_come_from_the_byte_gate(self) -> None:
        # Size is still enforced, by the layer that knows sizes.
        with (
            _NO_GTT,
            patch(
                "cohezion.compound.oom_guard._catalog_entry",
                return_value={"id": "Gemma-4-31B-it-GGUF", "size": 19.0, "recipe": "llamacpp"},
            ),
        ):
            d = _gate(resident=[], available_gb=20.0).decide("Gemma-4-31B-it-GGUF")
        assert d.allow is False
        assert "aperture" not in d.reason
