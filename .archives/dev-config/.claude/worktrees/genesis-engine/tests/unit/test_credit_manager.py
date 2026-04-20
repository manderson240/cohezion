"""Tests for the CreditManager (cohezion.core.credit_manager)."""

from __future__ import annotations

import cohezion.core.credit_manager as cm_module
from cohezion.core.credit_manager import (
    FALLBACK_MODEL,
    MODEL_COSTS,
    CreditManager,
    get_credit_manager,
)


class TestCreditManagerInit:
    def test_default_credits(self):
        mgr = CreditManager()
        assert mgr.get_balance("agent_x") == 100

    def test_custom_default_credits(self):
        mgr = CreditManager(default_credits=500)
        assert mgr.get_balance("agent_x") == 500


class TestBalanceOps:
    def setup_method(self):
        self.mgr = CreditManager(default_credits=100)

    def test_get_balance_default(self):
        assert self.mgr.get_balance("new_agent") == 100

    def test_credit_adds_to_balance(self):
        self.mgr.credit("agent_a", 50)
        assert self.mgr.get_balance("agent_a") == 150

    def test_deduct_success(self):
        result = self.mgr.deduct("agent_a", 30)
        assert result is True
        assert self.mgr.get_balance("agent_a") == 70

    def test_deduct_exact_balance(self):
        result = self.mgr.deduct("agent_a", 100)
        assert result is True
        assert self.mgr.get_balance("agent_a") == 0

    def test_deduct_insufficient_funds(self):
        result = self.mgr.deduct("agent_a", 200)
        assert result is False
        assert self.mgr.get_balance("agent_a") == 100  # Unchanged

    def test_credit_then_deduct(self):
        self.mgr.credit("agent_a", 50)
        self.mgr.deduct("agent_a", 120)
        assert self.mgr.get_balance("agent_a") == 30

    def test_multiple_agents_independent(self):
        self.mgr.deduct("agent_a", 50)
        self.mgr.credit("agent_b", 100)
        assert self.mgr.get_balance("agent_a") == 50
        assert self.mgr.get_balance("agent_b") == 200


class TestModelCosts:
    def setup_method(self):
        self.mgr = CreditManager(default_credits=100)

    def test_known_model_cost(self):
        assert self.mgr.get_model_cost("phi3:mini") == 1
        assert self.mgr.get_model_cost("deepseek-r1:70b") == 15

    def test_unknown_model_defaults_to_5(self):
        assert self.mgr.get_model_cost("unknown-model:latest") == 5

    def test_can_afford_cheap_model(self):
        assert self.mgr.can_afford("agent_a", "phi3:mini") is True

    def test_cannot_afford_expensive_model_with_low_balance(self):
        self.mgr._balances["broke_agent"] = 1
        assert self.mgr.can_afford("broke_agent", "deepseek-r1:70b") is False


class TestFallbackRouting:
    def setup_method(self):
        self.mgr = CreditManager(default_credits=100)

    def test_returns_preferred_if_affordable(self):
        result = self.mgr.get_best_affordable_model("agent_a", "phi3:mini")
        assert result == "phi3:mini"

    def test_fallback_to_cheaper_model(self):
        self.mgr._balances["agent_a"] = 2
        result = self.mgr.get_best_affordable_model("agent_a", "deepseek-r1:70b")
        # Should pick the most expensive affordable local model
        assert result in MODEL_COSTS
        assert MODEL_COSTS[result] <= 2

    def test_ultimate_fallback(self):
        self.mgr._balances["agent_a"] = 0
        result = self.mgr.get_best_affordable_model("agent_a", "deepseek-r1:70b")
        assert result == FALLBACK_MODEL

    def test_best_affordable_is_most_expensive_affordable(self):
        self.mgr._balances["agent_a"] = 8
        result = self.mgr.get_best_affordable_model("agent_a", "deepseek-r1:70b")
        # Should get qwen3-coder:32b (cost 8) which is the most expensive it can afford
        assert result == "qwen3-coder:32b"


class TestSingleton:
    def setup_method(self):
        cm_module._INSTANCE = None

    def test_get_credit_manager_creates_singleton(self):
        mgr = get_credit_manager()
        assert isinstance(mgr, CreditManager)

    def test_get_credit_manager_returns_same(self):
        mgr1 = get_credit_manager()
        mgr2 = get_credit_manager()
        assert mgr1 is mgr2

    def teardown_method(self):
        cm_module._INSTANCE = None
