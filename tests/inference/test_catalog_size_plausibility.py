"""RS7 — an implausible catalog size must not silently defeat the weights-fit gate.

Found 2026-08-04 while writing the corrected offloading profile: the live router reports
`Qwen3.6-35B-A3B-GGUF` at **1.68 GB**. A 35B model cannot be 1.68 GB — its MTP sibling
reports 22.10 GB. `_catalog_sizes()` trusts that field verbatim, so `ensure_resident` would
compute `needed = 1.68 + 1 = 2.68 GB`, PASS the gate against an 11.7 GB budget, and then
attempt a ~20 GB load.

That is exactly the blind cold load N3 item 5 forbids. `ensure_resident` already refuses a
model of UNKNOWN size ("unknown weight size — refusing blind cold load"); the hole is that a
WRONG size is worse than a missing one, because it looks like knowledge.

The guard infers a floor from the parameter count in the model name. At the most aggressive
quantisation anyone ships (~1 bit/weight ≈ 0.125 GB per billion params), a 35B cannot be under
~4 GB. A reported size below that floor is not a small model — it is bad metadata.
"""

from __future__ import annotations

import pytest

from cohezion.inference.hotswap import implausible_size_gb, params_b_from_name


class TestParamExtraction:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("Qwen3.6-35B-A3B-GGUF", 35.0),
            ("Gemma-4-26B-A4B-it-GGUF", 26.0),
            ("Bonsai-8B-gguf", 8.0),
            ("Qwen3-0.6B-GGUF", 0.6),
            ("mistralai_Mistral-Medium-3.5-128B-GGUF-IQ4_XS", 128.0),
            ("Bonsai-1.7B-gguf", 1.7),
        ],
    )
    def test_extracts_parameter_count(self, name, expected):
        assert params_b_from_name(name) == expected

    def test_DISCRIMINATING_ignores_the_ACTIVE_param_suffix(self):
        """`35B-A3B` is 35B total with 3B ACTIVE. MoE residency is driven by TOTAL — all
        experts must be reachable. Reading A3B as the size would under-gate by 10x."""
        assert params_b_from_name("Qwen3.6-35B-A3B-GGUF") == 35.0

    def test_DISCRIMINATING_version_numbers_are_not_parameter_counts(self):
        """'Gemma-4-26B': the 4 is a version. A naive first-number parse returns 4."""
        assert params_b_from_name("Gemma-4-26B-A4B-it-GGUF") == 26.0

    def test_returns_none_when_no_parameter_count_is_present(self):
        for n in ("nomic-embed-text-v2-moe-GGUF", "SD-Turbo", "kokoro-v1", ""):
            assert params_b_from_name(n) is None


class TestPlausibility:
    def test_DISCRIMINATING_the_real_case_is_rejected(self):
        """The live defect: 35B reported at 1.68 GB."""
        assert implausible_size_gb("Qwen3.6-35B-A3B-GGUF", 1.68) is True

    def test_POSITIVE_CONTROL_real_sizes_are_accepted(self):
        """Proves the guard is selective, not a blanket refusal. Every one of these is a
        genuine size read from the live catalog today."""
        for name, gb in [
            ("Qwen3.6-35B-A3B-MTP-GGUF", 22.10),
            ("Gemma-4-26B-A4B-it-GGUF", 16.90),
            ("Bonsai-8B-gguf", 1.08),
            ("Qwen3-0.6B-GGUF", 0.36),
            ("mistralai_Mistral-Medium-3.5-128B-GGUF-IQ4_XS", 42.30),
            ("Bonsai-27B-gguf-Q1_0", 4.41),  # genuinely Q1_0 — must NOT be rejected
        ]:
            assert implausible_size_gb(name, gb) is False, f"{name} @ {gb}GB wrongly rejected"

    def test_unknown_parameter_count_is_never_implausible(self):
        """No params in the name means no floor to compare against — fail OPEN here, because
        the existing unknown-size path already handles genuinely missing sizes."""
        assert implausible_size_gb("nomic-embed-text-v2-moe-GGUF", 0.48) is False
        assert implausible_size_gb("SD-Turbo", 4.86) is False

    def test_zero_or_negative_size_is_implausible_when_params_are_known(self):
        assert implausible_size_gb("Bonsai-8B-gguf", 0.0) is True


class TestGateIntegration:
    def test_DISCRIMINATING_ensure_resident_refuses_the_mis_sized_model(self, monkeypatch):
        """The whole point: a wrong size must reach the same refusal as a missing one.
        Without the guard this ADMITS — needed=2.68GB against a 60GB budget — and then
        attempts a ~20GB load."""
        from cohezion.inference import hotswap as h

        loaded: list = []
        monkeypatch.setattr(h, "resident_models", lambda: [])
        monkeypatch.setattr(h, "_catalog_sizes", lambda: {"Qwen3.6-35B-A3B-GGUF": 1.68})
        monkeypatch.setattr(h, "free_gb", lambda: 76.0)
        monkeypatch.setattr(h, "_post", lambda *a, **k: (loaded.append(a), (200, "ok"))[1])

        res = h.ensure_resident("Qwen3.6-35B-A3B-GGUF")
        assert res.ok is False, "a 35B reported at 1.68GB was admitted"
        assert "implausible" in res.reason.lower()
        assert loaded == [], "attempted the load despite bad metadata"

    def test_POSITIVE_CONTROL_a_correctly_sized_model_still_loads(self, monkeypatch):
        from cohezion.inference import hotswap as h

        posted: list = []

        def _resident():
            """State-based: empty before the load, resident after. A static [] makes the
            STRICT post-load verification fail for the wrong reason and would hide whether
            the plausibility guard was the thing rejecting it."""
            if not posted:
                return []
            return [{"model_name": "Bonsai-8B-gguf", "loaded": True, "last_use": 1}]

        monkeypatch.setattr(h, "resident_models", _resident)
        monkeypatch.setattr(h, "_catalog_sizes", lambda: {"Bonsai-8B-gguf": 1.08})
        monkeypatch.setattr(h, "free_gb", lambda: 76.0)
        monkeypatch.setattr(h, "_post", lambda *a, **k: (posted.append(a), (200, "ok"))[1])
        assert h.ensure_resident("Bonsai-8B-gguf").ok is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
