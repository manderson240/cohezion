"""Tests for Gemma 4 Router."""

import pytest

from cohezion.swarm.gemma4_router import Gemma4Router, RoutingDecision


class TestGemma4Router:
    def test_routing_logic_light(self):
        router = Gemma4Router()
        decision = router.route("What is the capital of France?")
        assert isinstance(decision, RoutingDecision)
        assert decision.model_id == "gemma4:2b"

    def test_routing_logic_medium(self):
        router = Gemma4Router()
        decision = router.route("Summarize this short paragraph for me: " + "a" * 200)
        assert decision.model_id == "gemma4:4b"

    def test_routing_logic_complex(self):
        router = Gemma4Router()
        decision = router.route(
            "Please reason through this difficult math problem and explain your steps."
        )
        assert decision.model_id == "gemma4:26b"

    def test_routing_logic_simulation(self):
        router = Gemma4Router()
        decision = router.route(
            "Simulate the 12D manifold trajectories for an EVO interacting with a QGP plasma."
        )
        assert decision.model_id == "gemma4:31b"
