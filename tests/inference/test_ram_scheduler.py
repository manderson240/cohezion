"""Tests for RamScheduler — 96 GB ceiling enforcer.

Discriminating tests: a scheduler that ignores the ceiling or never evicts
would fail test_ceiling_triggers_eviction_recommendation and
test_small_models_fit_without_eviction.

All size data is provided via an injected FIXTURE_REGISTRY so no Lemonade
server is required.  Exact footprint assertions use the same sizes as
the real Lemonade registry (audited 2026-06-27).
"""

from __future__ import annotations

import pytest

from cohezion.inference.local_fleet import LocalResearchFleet
from cohezion.inference.ram_scheduler import (
    RAM_EFFECTIVE_GB,
    RamScheduler,
    get_scheduler,
    model_footprint,
)


# Minimal registry covering the models used in these tests.
# Mirrors real Lemonade size data so assertions stay discriminating.
FIXTURE_REGISTRY = [
    {"id": "llama3.2-1b-FLM", "size": 1.30, "max_context_window": 131072, "labels": []},
    {
        "id": "nomic-embed-text-v2-moe-GGUF",
        "size": 0.51,
        "max_context_window": 512,
        "labels": ["embeddings"],
    },
    {
        "id": "Gemma-4-E4B-it-GGUF",
        "size": 5.97,
        "max_context_window": 131072,
        "labels": ["vision", "tool-calling"],
    },
    {
        "id": "Gemma-4-31B-it-GGUF",
        "size": 19.50,
        "max_context_window": 262144,
        "labels": ["vision", "tool-calling"],
    },
    {
        "id": "Qwen3.6-35B-A3B-MTP-GGUF",
        "size": 23.80,
        "max_context_window": 262144,
        "labels": ["vision", "tool-calling", "mtp"],
    },
    {
        "id": "Nemotron-3-Nano-30B-A3B-GGUF",
        "size": 22.80,
        "max_context_window": 1048576,
        "labels": ["tool-calling"],
    },
    {
        "id": "Qwen3.6-35B-A3B-GGUF",
        "size": 23.30,
        "max_context_window": 262144,
        "labels": ["vision", "tool-calling", "hot"],
    },
    {
        "id": "Qwen3.5-35B-A3B-GGUF",
        "size": 23.10,
        "max_context_window": 262144,
        "labels": ["vision", "tool-calling"],
    },
]


def _fleet() -> LocalResearchFleet:
    return LocalResearchFleet(registry=FIXTURE_REGISTRY)


class TestModelFootprint:
    """model_footprint() must include KV-cache overhead."""

    def test_large_model_footprint_includes_overhead(self) -> None:
        # Gemma-4-31B is 19.5 GB; KV overhead for >10 GB models is +3 GB
        fp = model_footprint("Gemma-4-31B-it-GGUF", fleet=_fleet())
        assert fp == pytest.approx(22.5, abs=0.1), (
            f"Gemma-4-31B footprint should be ~22.5 GB (19.5 + 3); got {fp}"
        )

    def test_small_model_footprint_includes_small_overhead(self) -> None:
        # llama3.2-1b-FLM is 1.3 GB; KV overhead is +1 GB
        fp = model_footprint("llama3.2-1b-FLM", fleet=_fleet())
        assert fp == pytest.approx(2.3, abs=0.1)

    def test_unknown_model_gets_default_footprint(self) -> None:
        fp = model_footprint("unknown-model-xyz", fleet=_fleet())
        # Default: 5.0 GB + 1 GB overhead
        assert fp == pytest.approx(6.0, abs=0.5)


class TestCeilingEnforcement:
    """RamScheduler must enforce the 88 GB effective ceiling."""

    def setup_method(self) -> None:
        self.fleet = _fleet()
        self.sched = RamScheduler(
            effective_ceiling_gb=RAM_EFFECTIVE_GB,
            fleet=self.fleet,
        )

    def test_small_models_fit_without_eviction(self) -> None:
        """Discriminating: a broken scheduler always recommends eviction."""
        to_evict = self.sched.ensure_loaded("llama3.2-1b-FLM")
        assert to_evict == [], f"Small model should not need eviction; got {to_evict}"

    def test_second_small_model_still_no_eviction(self) -> None:
        self.sched.ensure_loaded("llama3.2-1b-FLM")
        to_evict = self.sched.ensure_loaded("nomic-embed-text-v2-moe-GGUF")
        assert to_evict == []

    def test_ceiling_triggers_eviction_recommendation(self) -> None:
        """Discriminating: pre-load >78 GB of large models, then add one more."""
        # Pre-fill with large models until we're near the ceiling:
        # 26.8 + 25.8 + 26.3 = 78.9 GB  (size + 3 GB KV each)
        large_models = [
            "Qwen3.6-35B-A3B-MTP-GGUF",  # 23.8 + 3 = 26.8 GB
            "Nemotron-3-Nano-30B-A3B-GGUF",  # 22.8 + 3 = 25.8 GB
            "Qwen3.6-35B-A3B-GGUF",  # 23.3 + 3 = 26.3 GB
        ]
        for mid in large_models:
            self.sched.ensure_loaded(mid)

        # Current usage: ~78.9 GB — adding another 26.1 GB overflows 88 GB
        to_evict = self.sched.ensure_loaded("Qwen3.5-35B-A3B-GGUF")
        assert len(to_evict) > 0, "Expected eviction recommendation when ceiling would be exceeded"

    def test_eviction_removes_from_lru(self) -> None:
        self.sched.ensure_loaded("Qwen3.6-35B-A3B-MTP-GGUF")
        self.sched.record_eviction("Qwen3.6-35B-A3B-MTP-GGUF")
        status = self.sched.status()
        assert "Qwen3.6-35B-A3B-MTP-GGUF" not in status.loaded_models

    def test_already_loaded_model_needs_no_eviction(self) -> None:
        self.sched.ensure_loaded("Gemma-4-E4B-it-GGUF")
        to_evict = self.sched.ensure_loaded("Gemma-4-E4B-it-GGUF")
        assert to_evict == [], "Repeat load should not recommend eviction"


class TestRamStatus:
    """status() must accurately reflect current RAM usage."""

    def setup_method(self) -> None:
        self.fleet = _fleet()
        self.sched = RamScheduler(fleet=self.fleet)

    def test_empty_scheduler_has_zero_usage(self) -> None:
        status = self.sched.status()
        assert status.estimated_gb == 0.0
        assert status.loaded_models == []
        assert not status.at_risk

    def test_loading_large_model_adds_to_usage(self) -> None:
        self.sched.ensure_loaded("Gemma-4-31B-it-GGUF")  # 19.5 + 3 = 22.5 GB
        status = self.sched.status()
        assert status.estimated_gb > 10.0
        assert "Gemma-4-31B-it-GGUF" in status.loaded_models

    def test_at_risk_when_headroom_under_12gb(self) -> None:
        # Fill to ~78.9 GB (88 - 12 = 76 threshold for at_risk)
        for mid in [
            "Qwen3.6-35B-A3B-MTP-GGUF",  # 26.8 GB
            "Nemotron-3-Nano-30B-A3B-GGUF",  # 25.8 GB
            "Qwen3.6-35B-A3B-GGUF",  # 26.3 GB
        ]:
            self.sched.ensure_loaded(mid)
        status = self.sched.status()
        # ~78.9 GB used → headroom ~9 GB → at_risk=True
        assert status.at_risk, f"Expected at_risk=True at {status.estimated_gb:.1f} GB"

    def test_reset_clears_state(self) -> None:
        self.sched.ensure_loaded("Gemma-4-E4B-it-GGUF")
        self.sched.reset()
        status = self.sched.status()
        assert status.estimated_gb == 0.0
        assert status.loaded_models == []


class TestSchedulerSingleton:
    def test_singleton_returns_same_object(self) -> None:
        s1 = get_scheduler()
        s2 = get_scheduler()
        assert s1 is s2

    def test_can_load_new_model_fresh(self) -> None:
        sched = RamScheduler(fleet=_fleet())
        assert sched.can_load("llama3.2-1b-FLM")

    def test_can_load_returns_true_for_already_loaded(self) -> None:
        sched = RamScheduler(fleet=_fleet())
        sched.ensure_loaded("Gemma-4-E4B-it-GGUF")
        assert sched.can_load("Gemma-4-E4B-it-GGUF")
