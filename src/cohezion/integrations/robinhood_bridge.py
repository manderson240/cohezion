"""RobinhoodBridge — intent parsing and safety gates for Robinhood orders (stub).

Exports consumed by tests/integrations/test_robinhood_bridge.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TradeAction(StrEnum):
    """Valid trade actions."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradeIntent:
    """A parsed trade intent extracted from natural language."""

    action: TradeAction
    symbol: str | None = None
    quantity: float | None = None
    order_type: str | None = None
    limit_price: float | None = None
    reasoning: str = ""


@dataclass
class IntentAnalysis:
    """Result of analyzing a natural-language trade request."""

    intent: TradeIntent
    confidence: float
    safety_flags: list[str]


@dataclass
class OrderProposal:
    """A proposed order derived from an intent analysis."""

    action: TradeAction
    symbol: str
    quantity: float
    order_type: str
    limit_price: float | None = None
    estimated_cost_usd: float = 0.0


class RobinhoodBridge:
    """Parse natural-language trade requests and apply safety gates."""

    def __init__(
        self,
        *,
        lemonade_url: str = "http://localhost:13305",
        surreal_url: str = "http://localhost:8001",
        max_order_usd: float = 10_000.0,
    ) -> None:
        self.lemonade_url = lemonade_url
        self.surreal_url = surreal_url
        self.max_order_usd = max_order_usd

    async def parse_intent(self, message: str) -> IntentAnalysis:
        """Parse *message* into a TradeIntent via Lemonade."""
        raise NotImplementedError

    async def propose_order(self, analysis: IntentAnalysis) -> OrderProposal | None:
        """Build an OrderProposal from *analysis*, applying safety gates.

        Returns None when the safety gates block the order.
        """
        raise NotImplementedError
