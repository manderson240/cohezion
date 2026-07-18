"""Unit tests for the idle-eviction sweep policy (no network)."""

from __future__ import annotations

from cohezion.inference.idle_eviction import eligible, observe_idle_minutes


def _gpu_llm(**over):
    m = {"device": "gpu", "type": "llm", "pinned": False}
    m.update(over)
    return m


class TestEligibility:
    def test_heavy_idle_gpu_model_is_eligible(self):
        assert eligible(_gpu_llm(), idle_minutes=45.0, size_gb=22.1)

    def test_npu_occupant_never_evicted(self):
        # Discriminating: gauntlet owns the NPU slot regardless of idle/size.
        assert not eligible(_gpu_llm(device="npu"), idle_minutes=999.0, size_gb=20.0)

    def test_embedding_models_never_evicted(self):
        assert not eligible(_gpu_llm(type="embedding"), idle_minutes=999.0, size_gb=10.0)

    def test_pinned_models_never_evicted(self):
        assert not eligible(_gpu_llm(pinned=True), idle_minutes=999.0, size_gb=20.0)

    def test_light_models_not_worth_evicting(self):
        assert not eligible(_gpu_llm(), idle_minutes=999.0, size_gb=5.5)

    def test_recently_used_not_evicted(self):
        assert not eligible(_gpu_llm(), idle_minutes=29.9, size_gb=22.1)

    def test_unknown_size_is_conservative_no_evict(self):
        assert not eligible(_gpu_llm(), idle_minutes=999.0, size_gb=None)


class TestIdleObservation:
    def test_first_sight_is_zero_idle(self):
        # Discriminating: last_use clock base is unknown — a model must not be
        # evictable the first time we ever observe it, however old its counter.
        state = {}
        assert observe_idle_minutes(state, "m", last_use=123, now=1000.0) == 0.0

    def test_unchanged_last_use_accrues_idle_time(self):
        state = {}
        observe_idle_minutes(state, "m", last_use=123, now=1000.0)
        assert observe_idle_minutes(state, "m", last_use=123, now=1000.0 + 31 * 60) == 31.0

    def test_changed_last_use_resets_clock(self):
        state = {}
        observe_idle_minutes(state, "m", last_use=123, now=1000.0)
        assert observe_idle_minutes(state, "m", last_use=456, now=1000.0 + 31 * 60) == 0.0
