"""Unit tests for RobinhoodBridge intent parsing and safety gates.

Mocks:
- httpx.AsyncClient (Lemonade OmniRouter + SurrealDB) — no live calls
- All assertions target observable behavior, not mock existence
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.integrations.robinhood_bridge import (
    IntentAnalysis,
    OrderProposal,
    RobinhoodBridge,
    TradeAction,
    TradeIntent,
)


# ── Test helpers ──────────────────────────────────────────────────────────────


def _lemonade_response(
    action: str,
    symbol: str | None = None,
    quantity=None,
    order_type: str | None = None,
    limit_price=None,
    reasoning: str = "test",
):
    """Build a Lemonade-style chat completion response containing JSON."""
    payload = {
        "action": action,
        "symbol": symbol,
        "quantity": quantity,
        "order_type": order_type,
        "limit_price": limit_price,
        "reasoning": reasoning,
    }
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"choices": [{"message": {"content": json.dumps(payload)}}]}
    resp.raise_for_status = MagicMock()
    return resp


def _surreal_ok():
    resp = MagicMock()
    resp.status_code = 200
    return resp


def _http_error(status: int):
    resp = MagicMock()
    resp.status_code = status
    resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp


class _FakeAsyncClient:
    """Intercepts POST calls and returns configured responses."""

    def __init__(self, lemonade_resp, surreal_resp=None):
        self._lemonade = lemonade_resp
        self._surreal = surreal_resp or _surreal_ok()
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url: str, **kwargs):
        body = kwargs.get("json") or {}
        self.calls.append((url, body))
        if "13305" in url or "chat/completions" in url:
            return self._lemonade
        return self._surreal


# ── TradeAction unit tests ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestTradeActionEnum:
    def test_read_only_actions(self):
        for action in (
            TradeAction.QUERY_PORTFOLIO,
            TradeAction.QUERY_POSITIONS,
            TradeAction.QUERY_BALANCES,
            TradeAction.QUERY_NEWS,
            TradeAction.UNKNOWN,
        ):
            assert action.is_read_only, f"{action} should be read-only"

    def test_order_actions_not_read_only(self):
        for action in (
            TradeAction.PROPOSE_BUY,
            TradeAction.PROPOSE_SELL,
            TradeAction.PROPOSE_REBALANCE,
        ):
            assert not action.is_read_only, f"{action} should not be read-only"

    def test_mcp_tool_buy_maps_to_place_order(self):
        assert TradeAction.PROPOSE_BUY.mcp_tool == "place_order"

    def test_mcp_tool_sell_maps_to_place_order(self):
        assert TradeAction.PROPOSE_SELL.mcp_tool == "place_order"

    def test_mcp_tool_portfolio_maps_to_get_portfolio(self):
        assert TradeAction.QUERY_PORTFOLIO.mcp_tool == "get_portfolio"

    def test_mcp_tool_rebalance_maps_to_rebalance_portfolio(self):
        assert TradeAction.PROPOSE_REBALANCE.mcp_tool == "rebalance_portfolio"

    def test_mcp_tool_unknown_is_none(self):
        assert TradeAction.UNKNOWN.mcp_tool is None


# ── OrderProposal.summary tests ───────────────────────────────────────────────


@pytest.mark.unit
class TestOrderProposalSummary:
    def _make_intent(self, action, symbol=None, qty=None, order_type=None, lp=None):
        return TradeIntent(
            action=action,
            symbol=symbol,
            quantity=qty,
            order_type=order_type,
            limit_price=lp,
        )

    def test_buy_market_summary(self):
        intent = self._make_intent(TradeAction.PROPOSE_BUY, "AAPL", 10.0, "market")
        proposal = OrderProposal(intent=intent, mcp_tool="place_order", mcp_params={})
        assert proposal.summary() == "BUY 10.0 shares of AAPL (MARKET)"

    def test_sell_limit_with_price(self):
        intent = self._make_intent(TradeAction.PROPOSE_SELL, "NVDA", 5.0, "limit", 900.0)
        proposal = OrderProposal(intent=intent, mcp_tool="place_order", mcp_params={})
        assert "SELL" in proposal.summary()
        assert "NVDA" in proposal.summary()
        assert "$900.00" in proposal.summary()

    def test_missing_symbol_shows_question_mark(self):
        intent = self._make_intent(TradeAction.PROPOSE_BUY, None, 3.0)
        proposal = OrderProposal(intent=intent, mcp_tool="place_order", mcp_params={})
        assert "?" in proposal.summary()

    def test_no_order_type_no_parentheses(self):
        intent = self._make_intent(TradeAction.PROPOSE_BUY, "TSLA", 1.0)
        proposal = OrderProposal(intent=intent, mcp_tool="place_order", mcp_params={})
        assert "(" not in proposal.summary()


# ── RobinhoodBridge.analyze — readonly_mode guard ─────────────────────────────


@pytest.mark.unit
class TestReadonlyModeGuard:
    """readonly_mode=True (default) must block any order proposal."""

    @pytest.fixture
    def bridge(self):
        return RobinhoodBridge(
            readonly_mode=True,
            lemonade_url="http://localhost:13305",
            surreal_url="http://localhost:8001",
        )

    @pytest.mark.asyncio
    async def test_propose_buy_blocked_in_readonly(self, bridge):
        client = _FakeAsyncClient(_lemonade_response("propose_buy", "AAPL", 5.0, "market"))
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("buy 5 shares of AAPL")

        assert isinstance(result, IntentAnalysis)
        assert result.proposal is None
        assert result.requires_confirmation is False
        assert "readonly_mode=True" in result.telegram_reply

    @pytest.mark.asyncio
    async def test_propose_sell_blocked_in_readonly(self, bridge):
        client = _FakeAsyncClient(_lemonade_response("propose_sell", "TSLA", 2.0, "market"))
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("sell 2 shares of TSLA")

        assert result.proposal is None
        assert "readonly_mode" in result.telegram_reply.lower()

    @pytest.mark.asyncio
    async def test_query_allowed_in_readonly(self, bridge):
        client = _FakeAsyncClient(_lemonade_response("query_portfolio"))
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("show my portfolio")

        assert result.requires_confirmation is False
        assert result.proposal is None
        # Reply should reference the MCP tool, not a block message
        assert "get_portfolio" in result.telegram_reply


# ── RobinhoodBridge.analyze — order proposal flow ────────────────────────────


@pytest.mark.unit
class TestOrderProposalFlow:
    """With readonly_mode=False, order intents produce a proposal requiring confirmation."""

    @pytest.fixture
    def bridge(self):
        return RobinhoodBridge(
            readonly_mode=False,
            lemonade_url="http://localhost:13305",
            surreal_url="http://localhost:8001",
        )

    @pytest.mark.asyncio
    async def test_limit_buy_produces_proposal(self, bridge):
        client = _FakeAsyncClient(
            _lemonade_response(
                "propose_buy", "NVDA", 5.0, "limit", 900.0, "User wants limit buy NVDA"
            )
        )
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("buy 5 NVDA at $900 limit")

        assert result.requires_confirmation is True
        assert result.proposal is not None
        assert result.proposal.mcp_tool == "place_order"
        assert result.proposal.mcp_params["symbol"] == "NVDA"
        assert result.proposal.mcp_params["side"] == "buy"
        assert result.proposal.mcp_params["quantity"] == 5.0
        assert result.proposal.mcp_params["limit_price"] == 900.0

    @pytest.mark.asyncio
    async def test_market_sell_proposal_params(self, bridge):
        client = _FakeAsyncClient(
            _lemonade_response("propose_sell", "AAPL", 3.0, "market", reasoning="sell AAPL")
        )
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("sell 3 AAPL")

        assert result.proposal is not None
        assert result.proposal.mcp_params["side"] == "sell"
        assert result.proposal.mcp_params["order_type"] == "market"
        assert "limit_price" not in result.proposal.mcp_params

    @pytest.mark.asyncio
    async def test_reply_contains_pending_confirmation_marker(self, bridge):
        client = _FakeAsyncClient(_lemonade_response("propose_buy", "MSFT", 1.0, "market"))
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("buy 1 MSFT")

        assert "PENDING CONFIRMATION" in result.telegram_reply
        assert "/confirm" in result.telegram_reply
        assert "/cancel" in result.telegram_reply

    @pytest.mark.asyncio
    async def test_reply_echoes_exact_mcp_params(self, bridge):
        """Discriminating: proposal reply must include the structured params, not just a summary."""
        client = _FakeAsyncClient(_lemonade_response("propose_buy", "NVDA", 7.0, "limit", 875.50))
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("buy 7 NVDA limit 875.50")

        # The raw params JSON must appear in the reply — not just a human summary
        assert '"symbol"' in result.telegram_reply
        assert '"NVDA"' in result.telegram_reply
        assert "875.5" in result.telegram_reply


# ── JSON parse robustness ─────────────────────────────────────────────────────


@pytest.mark.unit
class TestLemonadeJsonParse:
    """_parse_lemonade_json must handle markdown fences and bad JSON gracefully."""

    @pytest.fixture
    def bridge(self):
        return RobinhoodBridge(
            readonly_mode=True,
            lemonade_url="http://localhost:13305",
            surreal_url="http://localhost:8001",
        )

    def test_clean_json_parsed(self, bridge):
        intent = bridge._parse_lemonade_json(
            '{"action": "query_portfolio", "symbol": null, "quantity": null, '
            '"order_type": null, "limit_price": null, "reasoning": "portfolio view"}',
            raw_text="show portfolio",
        )
        assert intent.action == TradeAction.QUERY_PORTFOLIO
        assert intent.symbol is None

    def test_markdown_fenced_json_parsed(self, bridge):
        content = '```json\n{"action": "query_positions", "symbol": "AAPL", "quantity": null, "order_type": null, "limit_price": null, "reasoning": "positions for AAPL"}\n```'
        intent = bridge._parse_lemonade_json(content, raw_text="my AAPL positions")
        assert intent.action == TradeAction.QUERY_POSITIONS
        assert intent.symbol == "AAPL"

    def test_invalid_json_falls_back_to_unknown(self, bridge):
        intent = bridge._parse_lemonade_json("not json at all", raw_text="foo")
        assert intent.action == TradeAction.UNKNOWN

    def test_unknown_action_value_falls_back(self, bridge):
        intent = bridge._parse_lemonade_json(
            '{"action": "delete_account", "symbol": null, "quantity": null, '
            '"order_type": null, "limit_price": null, "reasoning": "bad"}',
            raw_text="bad action",
        )
        assert intent.action == TradeAction.UNKNOWN

    def test_numeric_quantity_and_price_parsed(self, bridge):
        intent = bridge._parse_lemonade_json(
            '{"action": "propose_buy", "symbol": "GME", "quantity": 100, '
            '"order_type": "limit", "limit_price": 25.5, "reasoning": "yolo"}',
            raw_text="buy GME",
        )
        assert intent.quantity == 100.0
        assert intent.limit_price == 25.5

    def test_string_quantity_coerced_to_float(self, bridge):
        intent = bridge._parse_lemonade_json(
            '{"action": "propose_sell", "symbol": "SPY", "quantity": "3", '
            '"order_type": "market", "limit_price": null, "reasoning": "sell SPY"}',
            raw_text="sell SPY",
        )
        assert intent.quantity == 3.0

    def test_fenced_json_without_language_tag(self, bridge):
        content = '```\n{"action": "query_balances", "symbol": null, "quantity": null, "order_type": null, "limit_price": null, "reasoning": "check balance"}\n```'
        intent = bridge._parse_lemonade_json(content, raw_text="my balance")
        assert intent.action == TradeAction.QUERY_BALANCES


# ── Lemonade failure resilience ───────────────────────────────────────────────


@pytest.mark.unit
class TestLemonadeFailureResilience:
    """On Lemonade failure, analyze() must return UNKNOWN gracefully (not raise)."""

    @pytest.fixture
    def bridge(self):
        return RobinhoodBridge(
            readonly_mode=True,
            lemonade_url="http://localhost:13305",
            surreal_url="http://localhost:8001",
        )

    @pytest.mark.asyncio
    async def test_lemonade_http_error_returns_unknown(self, bridge):
        client = _FakeAsyncClient(_http_error(500))
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("do something")

        assert result.intent.action == TradeAction.UNKNOWN
        assert result.requires_confirmation is False

    @pytest.mark.asyncio
    async def test_lemonade_network_error_returns_unknown(self, bridge):
        bad_client = MagicMock()
        bad_client.__aenter__ = AsyncMock(side_effect=Exception("connection refused"))
        bad_client.__aexit__ = AsyncMock(return_value=False)
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=bad_client,
        ):
            result = await bridge.analyze("buy AAPL")

        assert result.intent.action == TradeAction.UNKNOWN

    @pytest.mark.asyncio
    async def test_surreal_failure_is_non_fatal(self, bridge):
        """SurrealDB log failure must not propagate — audit log is best-effort."""
        call_count = 0

        class _SelectiveClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, **kwargs):
                nonlocal call_count
                call_count += 1
                if "13305" in url or "chat" in url:
                    return _lemonade_response("query_portfolio")
                raise Exception("SurrealDB down")

        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=_SelectiveClient(),
        ):
            result = await bridge.analyze("show portfolio")

        # Despite SurrealDB failure, we still get a valid result
        assert result.intent.action == TradeAction.QUERY_PORTFOLIO


# ── Query reply formatting ────────────────────────────────────────────────────


@pytest.mark.unit
class TestQueryReplyFormatting:
    @pytest.fixture
    def bridge(self):
        return RobinhoodBridge()

    @pytest.mark.asyncio
    async def test_news_query_includes_symbol(self, bridge):
        client = _FakeAsyncClient(
            _lemonade_response("query_news", "TSLA", reasoning="news for TSLA")
        )
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("news about TSLA")

        assert "TSLA" in result.telegram_reply

    @pytest.mark.asyncio
    async def test_unknown_action_shows_help_text(self, bridge):
        client = _FakeAsyncClient(_lemonade_response("unknown", reasoning="unclear intent"))
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("do something weird")

        assert (
            "portfolio" in result.telegram_reply.lower() or "try:" in result.telegram_reply.lower()
        )

    @pytest.mark.asyncio
    async def test_portfolio_reply_includes_mcp_tool_name(self, bridge):
        client = _FakeAsyncClient(_lemonade_response("query_portfolio"))
        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=client,
        ):
            result = await bridge.analyze("show my portfolio")

        assert "get_portfolio" in result.telegram_reply

    @pytest.mark.asyncio
    async def test_lemonade_called_with_correct_model(self, bridge):
        """Discriminating: must use Gemma-4-E4B-it-GGUF, not some other model."""
        captured = {}

        class _CapturingClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, **kwargs):
                if "13305" in url:
                    captured["body"] = kwargs.get("json", {})
                    return _lemonade_response("query_balances")
                return _surreal_ok()

        with patch(
            "cohezion.integrations.robinhood_bridge.httpx.AsyncClient",
            return_value=_CapturingClient(),
        ):
            await bridge.analyze("what is my balance")

        assert captured["body"].get("model") == "Gemma-4-E4B-it-GGUF"
        assert captured["body"].get("temperature") == 0.0
