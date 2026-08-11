"""Unit tests for cohezion.inference.delegation_logger.DelegationLogger.

Tests
-----
1. EVI threshold gating: EVI < 0.75 must NOT escalate (returns False, no HTTP call).
2. EVI at threshold boundary: EVI == 0.75 MUST escalate.
3. Tier-1 → Tier-2 escalation: happy-path persistence + EventBus publish.
4. SurrealDB persistence is called with correct SQL payload.
5. EventBus publish is invoked even when SurrealDB fails.
6. Circuit breaker open: SurrealDB write skipped gracefully.
7. SurrealDB connection error: circuit records failure, returns False.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.inference.delegation_logger import (
    DelegationLogger,
    EVI_ESCALATION_THRESHOLD,
    EscalationRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_logger(**kwargs) -> DelegationLogger:
    """Create a DelegationLogger pointed at a test SurrealDB URL."""
    defaults = dict(
        surreal_url="http://localhost:8001",
        surreal_ns="test_ns",
        surreal_db="test_db",
        surreal_user="admin",
        surreal_pass="root",
        http_timeout=2.0,
    )
    defaults.update(kwargs)
    return DelegationLogger(**defaults)


# ---------------------------------------------------------------------------
# Test 1: EVI threshold gating — EVI < 0.75 must NOT escalate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evi_below_threshold_does_not_escalate():
    """EVI < 0.75 should return False and make no HTTP call."""
    dl = _make_logger()

    with patch.object(dl, "_persist_to_surreal", new_callable=AsyncMock) as mock_persist, \
         patch.object(dl, "_publish_event", new_callable=AsyncMock) as mock_event:

        result = await dl.log_escalation(
            task_class="reasoning",
            from_tier=1,
            to_tier=2,
            evi_score=0.70,   # below threshold
            reason="lemonade_unhealthy",
        )

    assert result is False
    mock_persist.assert_not_called()
    mock_event.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: EVI at threshold boundary (== 0.75) MUST escalate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evi_at_threshold_escalates():
    """EVI exactly at EVI_ESCALATION_THRESHOLD (0.75) should escalate."""
    dl = _make_logger()

    with patch.object(dl, "_persist_to_surreal", new_callable=AsyncMock, return_value=True) as mock_p, \
         patch.object(dl, "_publish_event", new_callable=AsyncMock):

        result = await dl.log_escalation(
            task_class="coding",
            from_tier=1,
            to_tier=2,
            evi_score=EVI_ESCALATION_THRESHOLD,
            reason="vram_saturated",
        )

    assert result is True
    mock_p.assert_called_once()


# ---------------------------------------------------------------------------
# Test 3: Tier-1 → Tier-2 happy-path escalation logging
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tier1_to_tier2_escalation_logging():
    """Happy path: Tier-1 → Tier-2 persists AND publishes."""
    dl = _make_logger()

    with patch.object(dl, "_persist_to_surreal", new_callable=AsyncMock, return_value=True) as mock_p, \
         patch.object(dl, "_publish_event", new_callable=AsyncMock) as mock_ev:

        result = await dl.log_escalation(
            task_class="reasoning",
            from_tier=1,
            to_tier=2,
            evi_score=0.88,
            reason="fleet_unhealthy",
        )

    assert result is True
    mock_p.assert_called_once()
    mock_ev.assert_called_once()

    # Verify the EscalationRecord passed to _persist has correct fields
    record: EscalationRecord = mock_p.call_args[0][0]
    assert record.task_class == "reasoning"
    assert record.from_tier == 1
    assert record.to_tier == 2
    assert abs(record.evi_score - 0.88) < 1e-9
    assert record.reason == "fleet_unhealthy"


# ---------------------------------------------------------------------------
# Test 4: SurrealDB persistence is called with correct SQL payload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_surreal_persistence_sql_content():
    """_persist_to_surreal should POST SQL containing task_class and tier info."""
    import httpx

    dl = _make_logger()

    captured_sql: list[str] = []

    class _FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

    async def _fake_post(url, *, content, headers, auth, **kwargs):
        captured_sql.append(content if isinstance(content, str) else content.decode())
        return _FakeResponse()

    # Patch the circuit breaker to allow requests
    mock_circuit = MagicMock()
    mock_circuit.allow_request.return_value = True

    with patch(
        "cohezion.inference.delegation_logger.get_circuit", return_value=mock_circuit
    ), patch.object(dl, "_publish_event", new_callable=AsyncMock), \
       patch("httpx.AsyncClient") as mock_client_cls:

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=_FakeResponse())
        mock_client_cls.return_value = mock_client

        await dl.log_escalation(
            task_class="vision",
            from_tier=1,
            to_tier=2,
            evi_score=0.91,
            reason="oom_guard",
        )

    # Check that post was called
    assert mock_client.post.called
    call_kwargs = mock_client.post.call_args
    sql_body = call_kwargs[1].get("content", "") or call_kwargs[0][1]
    assert "delegation_log" in sql_body
    assert "vision" in sql_body
    assert "oom_guard" in sql_body


# ---------------------------------------------------------------------------
# Test 5: EventBus publish fires even when SurrealDB fails
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_eventbus_published_even_on_surreal_failure():
    """EventBus event must be published regardless of SurrealDB failure."""
    dl = _make_logger()

    with patch.object(
        dl, "_persist_to_surreal", new_callable=AsyncMock, return_value=False
    ) as mock_p, patch.object(dl, "_publish_event", new_callable=AsyncMock) as mock_ev:

        result = await dl.log_escalation(
            task_class="research",
            from_tier=1,
            to_tier=2,
            evi_score=0.80,
            reason="circuit_open",
        )

    assert result is False  # persist returned False
    mock_ev.assert_called_once()  # EventBus still fired


# ---------------------------------------------------------------------------
# Test 6: Circuit breaker open — SurrealDB write skipped gracefully
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_circuit_open_skips_surreal_write():
    """When the circuit breaker is open, _persist_to_surreal returns False without HTTP call."""
    dl = _make_logger()

    mock_circuit = MagicMock()
    mock_circuit.allow_request.return_value = False  # circuit is OPEN

    with patch(
        "cohezion.inference.delegation_logger.get_circuit", return_value=mock_circuit
    ), patch("httpx.AsyncClient") as mock_http:

        record = EscalationRecord(
            task_class="fast_qa",
            from_tier=1,
            to_tier=2,
            evi_score=0.85,
            reason="test",
        )
        result = await dl._persist_to_surreal(record)

    assert result is False
    mock_http.assert_not_called()


# ---------------------------------------------------------------------------
# Test 7: SurrealDB connection error is handled gracefully
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_surreal_connection_error_handled_gracefully():
    """ConnectError on SurrealDB must not propagate; circuit records failure."""
    import httpx

    dl = _make_logger()

    mock_circuit = MagicMock()
    mock_circuit.allow_request.return_value = True

    with patch(
        "cohezion.inference.delegation_logger.get_circuit", return_value=mock_circuit
    ), patch("httpx.AsyncClient") as mock_client_cls:

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        mock_client_cls.return_value = mock_client

        record = EscalationRecord(
            task_class="coding",
            from_tier=1,
            to_tier=2,
            evi_score=0.90,
            reason="test_connection_failure",
        )
        result = await dl._persist_to_surreal(record)

    assert result is False
    mock_circuit.record_failure.assert_called_once()
