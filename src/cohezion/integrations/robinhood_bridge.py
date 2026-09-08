"""RobinhoodBridge — intent parsing and safety gates for Robinhood orders.

Exports consumed by tests/integrations/test_robinhood_bridge.py.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import StrEnum

import httpx


logger = logging.getLogger(__name__)


class TradeAction(StrEnum):
    """Valid trade actions."""

    PROPOSE_BUY = "propose_buy"
    PROPOSE_SELL = "propose_sell"
    PROPOSE_REBALANCE = "propose_rebalance"
    QUERY_PORTFOLIO = "query_portfolio"
    QUERY_POSITIONS = "query_positions"
    QUERY_BALANCES = "query_balances"
    QUERY_NEWS = "query_news"
    UNKNOWN = "unknown"

    @property
    def is_read_only(self) -> bool:
        return self in (
            TradeAction.QUERY_PORTFOLIO,
            TradeAction.QUERY_POSITIONS,
            TradeAction.QUERY_BALANCES,
            TradeAction.QUERY_NEWS,
            TradeAction.UNKNOWN,
        )

    @property
    def mcp_tool(self) -> str | None:
        match self:
            case TradeAction.PROPOSE_BUY | TradeAction.PROPOSE_SELL:
                return "place_order"
            case TradeAction.PROPOSE_REBALANCE:
                return "rebalance_portfolio"
            case TradeAction.QUERY_PORTFOLIO:
                return "get_portfolio"
            case TradeAction.QUERY_POSITIONS:
                return "get_positions"
            case TradeAction.QUERY_BALANCES:
                return "get_account_balances"
            case TradeAction.QUERY_NEWS:
                return "get_market_news"
            case _:
                return None


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
class OrderProposal:
    """A proposed order derived from an intent analysis."""

    intent: TradeIntent
    mcp_tool: str
    mcp_params: dict

    def summary(self) -> str:
        action_str = (
            "BUY"
            if self.intent.action == TradeAction.PROPOSE_BUY
            else "SELL"
            if self.intent.action == TradeAction.PROPOSE_SELL
            else str(self.intent.action.value).upper()
        )
        symbol_str = self.intent.symbol or "?"
        qty_str = f"{self.intent.quantity} shares of " if self.intent.quantity is not None else ""
        price_str = (
            f" at ${self.intent.limit_price:.2f}" if self.intent.limit_price is not None else ""
        )
        order_type_str = f" ({self.intent.order_type.upper()})" if self.intent.order_type else ""
        return f"{action_str} {qty_str}{symbol_str}{price_str}{order_type_str}"


@dataclass
class IntentAnalysis:
    """Result of analyzing a natural-language trade request."""

    intent: TradeIntent
    proposal: OrderProposal | None
    requires_confirmation: bool
    telegram_reply: str


class RobinhoodBridge:
    """Parse natural-language trade requests and apply safety gates."""

    def __init__(
        self,
        *,
        readonly_mode: bool = True,
        lemonade_url: str = "http://localhost:13305",
        surreal_url: str = "http://localhost:8001",
        max_order_usd: float = 10_000.0,
    ) -> None:
        self.readonly_mode = readonly_mode
        self.lemonade_url = lemonade_url
        self.surreal_url = surreal_url
        self.max_order_usd = max_order_usd

    def _parse_lemonade_json(self, content: str, raw_text: str = "") -> TradeIntent:
        text = content.strip()
        if "```" in text:
            lines = text.splitlines()
            code_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    code_lines.append(line)
            if code_lines:
                text = "\n".join(code_lines).strip()

        try:
            data = json.loads(text)
        except Exception:
            return TradeIntent(action=TradeAction.UNKNOWN, reasoning=raw_text)

        action_raw = data.get("action", "")
        try:
            action = TradeAction(action_raw)
        except ValueError:
            action = TradeAction.UNKNOWN

        symbol = data.get("symbol")
        quantity = data.get("quantity")
        if quantity is not None:
            try:
                quantity = float(quantity)
            except (ValueError, TypeError):
                quantity = None

        order_type = data.get("order_type")
        limit_price = data.get("limit_price")
        if limit_price is not None:
            try:
                limit_price = float(limit_price)
            except (ValueError, TypeError):
                limit_price = None

        reasoning = data.get("reasoning", "") or raw_text

        return TradeIntent(
            action=action,
            symbol=symbol,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            reasoning=reasoning,
        )

    async def analyze(self, message: str) -> IntentAnalysis:
        prompt = (
            "You are a trading intent extractor. Parse the user request into JSON with fields: "
            "action, symbol, quantity, order_type, limit_price, reasoning."
        )
        intent = TradeIntent(action=TradeAction.UNKNOWN)
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.lemonade_url}/v1/chat/completions"
                payload = {
                    "model": "Gemma-4-E4B-it-GGUF",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": message},
                    ],
                    "temperature": 0.0,
                }
                resp = await client.post(url, json=payload, timeout=10.0)
                resp.raise_for_status()
                body = resp.json()
                content = body["choices"][0]["message"]["content"]
                intent = self._parse_lemonade_json(content, raw_text=message)

                try:
                    surreal_payload = {"event": "trade_intent", "intent": intent.action.value}
                    await client.post(f"{self.surreal_url}/sql", json=surreal_payload, timeout=2.0)
                except Exception:
                    pass
        except Exception:
            intent = TradeIntent(action=TradeAction.UNKNOWN, reasoning=message)

        if not intent.action.is_read_only:
            if self.readonly_mode:
                return IntentAnalysis(
                    intent=intent,
                    proposal=None,
                    requires_confirmation=False,
                    telegram_reply=f"Order blocked: readonly_mode=True. Intent was {intent.action.value}.",
                )
            else:
                side = (
                    "buy"
                    if intent.action == TradeAction.PROPOSE_BUY
                    else "sell"
                    if intent.action == TradeAction.PROPOSE_SELL
                    else intent.action.value
                )
                mcp_params = {
                    "symbol": intent.symbol,
                    "side": side,
                    "quantity": intent.quantity,
                }
                if intent.order_type:
                    mcp_params["order_type"] = intent.order_type
                if intent.limit_price is not None:
                    mcp_params["limit_price"] = intent.limit_price

                proposal = OrderProposal(
                    intent=intent,
                    mcp_tool=intent.action.mcp_tool or "place_order",
                    mcp_params=mcp_params,
                )
                params_json = json.dumps(mcp_params)
                reply = (
                    f"PENDING CONFIRMATION: {proposal.summary()}\n"
                    f"MCP tool: {proposal.mcp_tool}\n"
                    f"Params: {params_json}\n"
                    f"Use /confirm or /cancel"
                )
                return IntentAnalysis(
                    intent=intent,
                    proposal=proposal,
                    requires_confirmation=True,
                    telegram_reply=reply,
                )
        else:
            mcp_tool = intent.action.mcp_tool
            if intent.action == TradeAction.UNKNOWN:
                reply = (
                    "Sorry, unknown action. Try: portfolio, positions, balances, news, or buy/sell."
                )
            else:
                tool_str = f"Using tool {mcp_tool}" if mcp_tool else ""
                symbol_str = f" for {intent.symbol}" if intent.symbol else ""
                reply = f"Query {intent.action.value}{symbol_str}. {tool_str}".strip()

            return IntentAnalysis(
                intent=intent,
                proposal=None,
                requires_confirmation=False,
                telegram_reply=reply,
            )
