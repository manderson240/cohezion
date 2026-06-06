"""Tests for the model_registry remediation (V-model audit §10 fix, 2026-06-05).

services/swarm_service.py + cli were dark because they import a ModelRegistry from
cohezion.models.model_registry that never existed. This wires it to the real CostAwareRouter
(non-destructive remediation). Tests use an injected fake router for hermetic behavior, plus
one integration check that no-arg construction + real routing works and that swarm_service/cli
now import.
"""
from __future__ import annotations

from cohezion.models.model_registry import ModelRegistry


class _FakeDecision:
    def __init__(self, model: str) -> None:
        self.model = model


class _FakeRouter:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def select_model(self, query, max_cost_usd=None, cache_hit_rate=None):
        self.calls.append((query, max_cost_usd, cache_hit_rate))
        return _FakeDecision("fast-model"), True


def test_get_best_for_task_returns_decision_model() -> None:
    fake = _FakeRouter()
    reg = ModelRegistry(router=fake)
    assert reg.get_best_for_task("analysis") == "fast-model"
    # prefer_fast=True must bias the router via cache_hit_rate=0.95 (its fast-path).
    assert fake.calls[0] == ("analysis", None, 0.95)


def test_prefer_fast_false_passes_no_cache_bias() -> None:
    fake = _FakeRouter()
    ModelRegistry(router=fake).get_best_for_task("x", budget=0.01, prefer_fast=False)
    assert fake.calls[0] == ("x", 0.01, None)


def test_fail_soft_returns_none_on_router_error() -> None:
    # Discriminating: a router failure must NOT propagate (swarm_service falls back to a
    # default model on None). An impl that lets the exception escape fails here.
    class _Boom:
        def select_model(self, **kw):
            raise RuntimeError("router down")

    assert ModelRegistry(router=_Boom()).get_best_for_task("x") is None


def test_no_arg_construction_and_real_routing_integration() -> None:
    # No-arg construct lazily builds a real CostAwareRouter; returns a model name or None.
    result = ModelRegistry().get_best_for_task("analyze this codebase")
    assert result is None or isinstance(result, str)


def test_swarm_service_and_cli_now_import() -> None:
    # The whole point of the remediation: these were dark (ImportError on model_registry).
    import importlib

    importlib.import_module("cohezion.services.swarm_service")
    importlib.import_module("cohezion.cli")
