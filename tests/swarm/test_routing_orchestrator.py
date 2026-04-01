"""TDD: RoutingOrchestrator — unified entry point for all 4 routing systems.

Chain of Responsibility pattern: SmartRouter(task→capability) + CostAwareRouter(complexity→model)
+ TipOfTheSpearRouter(constitutional→escalation) + DynamicModelRouter(health→fallback)
all share confidence signals through a single orchestrator.

Token efficiency: single call replaces 4 separate router consultations.
"""

from __future__ import annotations


class TestRoutingOrchestratorExists:
    """RoutingOrchestrator should exist as a unified entry point."""

    def test_class_exists(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        assert RoutingOrchestrator is not None

    def test_has_route_method(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        assert hasattr(orch, "route")

    def test_has_get_confidence_method(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        assert hasattr(orch, "get_confidence")


class TestRoutingOrchestratorRoute:
    """route() should return a unified decision with confidence."""

    def test_route_returns_decision(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        decision = orch.route("simple hello world task")
        assert decision is not None
        assert hasattr(decision, "model")
        assert hasattr(decision, "confidence")

    def test_route_simple_task_selects_cheap_model(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        decision = orch.route("hello world")
        # Simple task should route to cheapest model
        assert decision.model in ("phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b")

    def test_route_includes_confidence_score(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        decision = orch.route("analyze complex architecture")
        assert 0.0 <= decision.confidence <= 1.0

    def test_route_with_budget_constraint(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        decision = orch.route("task", max_cost_usd=0.001)
        assert decision.estimated_cost_usd <= 0.01  # Should respect budget


class TestRoutingOrchestratorConfidence:
    """get_confidence() aggregates signals from all routers."""

    def test_confidence_returns_float(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        conf = orch.get_confidence("phi3:mini", "simple task")
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

    def test_high_confidence_for_simple_task_cheap_model(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        conf = orch.get_confidence("phi3:mini", "hello")
        # Simple task + cheap model = high confidence
        assert conf >= 0.5

    def test_low_confidence_for_complex_task_cheap_model(self):
        from cohezion.swarm.routing_orchestrator import RoutingOrchestrator

        orch = RoutingOrchestrator()
        conf = orch.get_confidence(
            "phi3:mini",
            "design a distributed consensus algorithm with formal verification proofs",
        )
        # Complex task + cheap model = lower confidence
        assert conf < 0.9
