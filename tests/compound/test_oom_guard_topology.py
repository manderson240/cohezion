"""Discriminating tests for byte-aware topology resolution in oom_guard (2026-08-31).

Rebuild of the lost dreamy-exploring-noodle fix. The 08-15 and 08-31 freezes shared a root
cause: ``get_live_topology`` resolved unknown models via ``MODEL_FOOTPRINT_GB.get(name, 0.0)``
— the SAME fail-open ``check_oom_risk``'s own comments record having removed at its own call
site. Live consequence: ``uma_committed_gb = 0.89 GB`` against 13.9 GiB of actual GTT (15×
under-count); ``gpt-oss-20b`` read as 0.0 GB.

Each test fails a plausible wrong implementation:
  - a resolver that returns 0.0 for unknown names (the historical defect),
  - one that ignores the router catalog and always assumes,
  - a tier resolver that ignores the live ``device`` field,
  - a topology that never consults the resolver (consumption, not declaration).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from cohezion.compound.oom_guard import (
    MODEL_FOOTPRINT_GB,
    UNKNOWN_ASSUMED_GB,
    ComputeTier,
    _resolve_footprint_gb,
    _resolve_tier,
    get_active_uma_gb,
    get_live_topology,
)


class TestResolveFootprint:
    def test_unknown_model_never_reads_as_zero(self) -> None:
        # THE historical defect: .get(name, 0.0) made every unrecognised model invisible
        # to UMA accounting. Unknown + no catalog answer must fall to the assumed-heavy
        # constant, never 0.0.
        got = _resolve_footprint_gb("gpt-oss-20b", catalog_sizes={})
        assert got == UNKNOWN_ASSUMED_GB
        assert got > 0.0

    def test_known_model_prefers_table_over_catalog(self) -> None:
        # The curated table is ground truth for known names even when the catalog disagrees.
        name = "Bonsai-8B-gguf"
        got = _resolve_footprint_gb(name, catalog_sizes={name: 99.0})
        assert got == MODEL_FOOTPRINT_GB[name]

    def test_unknown_model_uses_catalog_size(self) -> None:
        # A wrong impl that jumps straight to UNKNOWN_ASSUMED_GB ignores the router's own
        # measurement — the LMX-Omni-52B lesson (44.77GB real vs 8GB assumed).
        got = _resolve_footprint_gb("gpt-oss-20b", catalog_sizes={"gpt-oss-20b": 12.5})
        assert got == 12.5


class TestResolveTier:
    def test_known_model_uses_static_table(self) -> None:
        assert _resolve_tier("llama3.2-1b-FLM", device="gpu") is ComputeTier.NPU

    def test_unknown_model_uses_live_device_field(self) -> None:
        # A wrong impl defaulting straight to IGPU would count NPU-resident FLM models
        # against the UMA pool (or miss CPU-resident ones).
        assert _resolve_tier("some-new-flm", device="npu") is ComputeTier.NPU
        assert _resolve_tier("some-tts", device="cpu") is ComputeTier.CPU
        assert _resolve_tier("some-gguf", device="gpu") is ComputeTier.IGPU

    def test_unknown_model_unknown_device_defaults_igpu(self) -> None:
        assert _resolve_tier("mystery", device="") is ComputeTier.IGPU


def _health_response(models: list[dict[str, str]]) -> MagicMock:
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"all_models_loaded": models}
    return resp


def _catalog_response(sizes: dict[str, float]) -> MagicMock:
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"data": [{"id": k, "size": v} for k, v in sizes.items()]}
    resp.raise_for_status.return_value = None
    return resp


class TestLiveTopologyConsumption:
    """get_live_topology must CONSUME the resolvers — not re-derive the fail-open."""

    @patch("cohezion.compound.oom_guard.httpx.get")
    def test_unknown_loaded_model_has_nonzero_footprint(self, mock_get: MagicMock) -> None:
        def route(url: str, **kwargs: object) -> MagicMock:
            if "/health" in url:
                return _health_response(
                    [{"model_name": "gpt-oss-20b", "backend_url": "", "device": "gpu"}]
                )
            return _catalog_response({})  # catalog has no answer either

        mock_get.side_effect = route
        topo = get_live_topology()
        assert len(topo) == 1
        # The wrong impl reports 0.0 here — exactly the 15× under-count.
        assert topo[0].footprint_gb == UNKNOWN_ASSUMED_GB

    @patch("cohezion.compound.oom_guard.httpx.get")
    def test_unknown_loaded_model_size_comes_from_catalog(self, mock_get: MagicMock) -> None:
        def route(url: str, **kwargs: object) -> MagicMock:
            if "/health" in url:
                return _health_response(
                    [{"model_name": "gpt-oss-20b", "backend_url": "", "device": "gpu"}]
                )
            return _catalog_response({"gpt-oss-20b": 13.9})

        mock_get.side_effect = route
        topo = get_live_topology()
        assert topo[0].footprint_gb == 13.9

    @patch("cohezion.compound.oom_guard.httpx.get")
    def test_active_uma_counts_unknown_models(self, mock_get: MagicMock) -> None:
        # Consumption invariant for the incident metric itself: uma_committed_gb must not
        # under-count when an unknown model is resident.
        def route(url: str, **kwargs: object) -> MagicMock:
            if "/health" in url:
                return _health_response(
                    [
                        {"model_name": "Bonsai-8B-gguf", "backend_url": "", "device": "gpu"},
                        {"model_name": "gpt-oss-20b", "backend_url": "", "device": "gpu"},
                    ]
                )
            return _catalog_response({"gpt-oss-20b": 13.9})

        mock_get.side_effect = route
        assert get_active_uma_gb() == MODEL_FOOTPRINT_GB["Bonsai-8B-gguf"] + 13.9

    @patch("cohezion.compound.oom_guard.httpx.get")
    def test_npu_device_model_excluded_from_uma(self, mock_get: MagicMock) -> None:
        # An unknown FLM model on the NPU must not inflate UMA committed bytes.
        def route(url: str, **kwargs: object) -> MagicMock:
            if "/health" in url:
                return _health_response(
                    [{"model_name": "some-new-flm", "backend_url": "", "device": "npu"}]
                )
            return _catalog_response({})

        mock_get.side_effect = route
        assert get_active_uma_gb() == 0.0

    @patch("cohezion.compound.oom_guard.httpx.get")
    def test_all_known_models_skip_catalog_fetch(self, mock_get: MagicMock) -> None:
        # Efficiency contract: when every loaded model is in the table, no catalog call.
        def route(url: str, **kwargs: object) -> MagicMock:
            if "/health" in url:
                return _health_response(
                    [{"model_name": "Bonsai-8B-gguf", "backend_url": "", "device": "gpu"}]
                )
            raise AssertionError("catalog must not be fetched when all names are known")

        mock_get.side_effect = route
        topo = get_live_topology()
        assert topo[0].footprint_gb == MODEL_FOOTPRINT_GB["Bonsai-8B-gguf"]
