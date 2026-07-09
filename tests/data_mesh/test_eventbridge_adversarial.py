"""Adversarial tests for DataMeshEventBridge.

Covers:
1. Direct _escape() unit tests (discriminating layer for injection defence)
2. SQL injection via event payload (json-encoded then string-escaped)
3. SQL injection via source field (string-escaped only)
4. Newline injection via source and payload
5. replay_since edge cases: 0.0, far-future, malformed-JSON payload, DB failure
6. Double-subscribe idempotency (documents double-write design bug)
7. SurrealDB write failure non-fatal resilience
8. BONUS: raw-interpolated timestamp/priority injection vector (real vulnerability)

Fixture note: `bridge._http` is replaced with a MagicMock after construction so that
`_ensure_schema` (called in __init__) never touches the real network. All subsequent
_handle and replay_since calls use the in-test mock exclusively.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.data_mesh.event_bridge import DataMeshEventBridge, _escape


# ── Character constants ────────────────────────────────────────────────────────
# Avoid Python string-literal escaping confusion in assertions.
BACKSLASH = chr(92)  # \
DQUOTE = chr(34)  # "
NEWLINE = chr(10)  # \n


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def bridge_and_mock():
    """Return (bridge, mock_http) with _ensure_schema hermetically mocked.

    Patches httpx.Client during DataMeshEventBridge.__init__ so _ensure_schema
    never hits the network, then resets mock so tests begin with call_count == 0.
    """
    with patch("cohezion.data_mesh.event_bridge.httpx.Client") as MockClient:
        b = DataMeshEventBridge()
        mock_http = MockClient.return_value
        mock_http.reset_mock()  # discard the _ensure_schema call
    # bridge._http still points to mock_http after the patch exits
    return b, mock_http


def _evt(
    *,
    event_type=EventType.DATA_PRODUCT_CREATED,
    source="test-source",
    payload=None,
    timestamp=1000.0,
    priority=0,
) -> Event:
    """Helper to create Event instances with convenient defaults."""
    return Event(
        type=event_type,
        source=source,
        payload=payload or {},
        timestamp=timestamp,
        priority=priority,
    )


def _last_sql(mock_http) -> str:
    """Extract SQL content from the most recent mock_http.post() call."""
    return mock_http.post.call_args.kwargs["content"]


def _expected_sql(bridge: DataMeshEventBridge, event: Event) -> str:
    """Build the expected SQL string by replicating _handle's escape logic.

    Used for golden-SQL equality checks: if _handle builds SQL differently,
    the delta reveals the bug. NOTE: this intentionally mirrors the implementation —
    the direct _escape() tests below are the discriminating layer that verifies
    _escape() itself is correct.
    """
    payload_json = _escape(json.dumps(event.payload))
    return (
        f"CREATE {bridge.TABLE} SET "
        f'event_type = "{event.type.name}", '
        f'source = "{_escape(event.source)}", '
        f"timestamp = {float(event.timestamp)}, "
        f'payload = "{payload_json}", '
        f"priority = {int(event.priority)};"
    )


# ── 1. Direct _escape() unit tests (discriminating layer) ────────────────────


class TestEscapeFunction:
    """Unit tests for _escape(). These are the discriminating layer.

    If _escape is broken, the golden-SQL tests in the injection classes
    would pass anyway (both sides produce the same wrong output). Testing
    _escape directly pins the correct behaviour independently.
    """

    def test_bare_double_quote_becomes_backslash_quote(self):
        """_escape converts lone " to \\\" (2-char sequence)."""
        result = _escape(DQUOTE)
        assert result == BACKSLASH + DQUOTE, (
            f"_escape({DQUOTE!r}) = {result!r}; expected backslash+quote"
        )

    def test_bare_backslash_is_doubled(self):
        """_escape doubles a lone backslash."""
        result = _escape(BACKSLASH)
        assert result == BACKSLASH + BACKSLASH, (
            f"_escape({BACKSLASH!r}) = {result!r}; expected double backslash"
        )

    def test_json_encoded_quote_sequence_4_chars(self):
        """DISCRIMINATING: json.dumps encodes a value-" as \\\" (2-char: \\ + ").

        _escape must then produce \\\\\\" (4 chars: \\ \\ \\ ") so SurrealQL
        reads \\\\ = one literal backslash, then \\" = one literal quote.

        If _escape only escaped the quote (not the preceding backslash first),
        the JSON-produced \\ before the \\" would survive and allow the closing
        double-quote to break out of the SQL string literal.
        """
        # 2-char input: backslash then double-quote (what json.dumps emits for " in value)
        json_encoded_quote = BACKSLASH + DQUOTE
        result = _escape(json_encoded_quote)

        # Step 1 (replace \\ with \\\\): \\" → \\\\" (3 chars: \\ \\ ")
        # Step 2 (replace " with \\"): \\\\" → \\\\\\" (4 chars: \\ \\ \\ ")
        expected = BACKSLASH * 3 + DQUOTE
        assert result == expected, (
            f"_escape({json_encoded_quote!r}) = {result!r} ({len(result)} chars); "
            f"expected {expected!r} ({len(expected)} chars). "
            "Wrong result means a json-encoded quote is NOT double-escaped, "
            "enabling the closing-quote SQL injection path."
        )

    def test_backslash_first_ordering_is_correct(self):
        """DISCRIMINATING: _escape must replace \\ before " (not the reverse).

        Wrong order (quote then backslash) produces a different — insecure — result
        for the \\\" sequence. This test verifies the actual ordering used.
        """
        s = BACKSLASH + DQUOTE  # 2-char input
        correct = s.replace(BACKSLASH, BACKSLASH * 2).replace(DQUOTE, BACKSLASH + DQUOTE)
        wrong = s.replace(DQUOTE, BACKSLASH + DQUOTE).replace(BACKSLASH, BACKSLASH * 2)
        assert correct != wrong, "Pre-condition: the two orderings must differ"
        assert _escape(s) == correct, (
            f"_escape uses wrong replacement order. "
            f"Got {_escape(s)!r}, correct-order gives {correct!r}"
        )

    def test_newline_replaced_with_backslash_n(self):
        """Literal \\n in string becomes \\\\n (two-char sequence, not raw newline)."""
        result = _escape("hello" + NEWLINE + "world")
        assert NEWLINE not in result, f"Raw newline in escaped output: {result!r}"
        assert BACKSLASH + "n" in result, "Escaped \\\\n must appear in output"

    def test_every_double_quote_in_output_has_preceding_backslash(self):
        """DISCRIMINATING: no bare double-quote in _escape output (all preceded by \\)."""
        evil = BACKSLASH + DQUOTE + NEWLINE + "; DROP TABLE x;" + DQUOTE * 3
        result = _escape(evil)
        for i, ch in enumerate(result):
            if ch == DQUOTE:
                assert i > 0 and result[i - 1] == BACKSLASH, (
                    f"Bare double-quote at position {i} in {result!r}; "
                    'every " in output must be preceded by \\'
                )


# ── 2. SQL injection via event payload ───────────────────────────────────────


class TestPayloadSQLInjection:
    pytestmark = pytest.mark.asyncio
    """Adversarial: malicious payload values must not break the SQL string literal."""

    async def test_embedded_quote_golden_sql(self, bridge_and_mock):
        """DISCRIMINATING (golden SQL): payload with \\\" produces correctly escaped SQL.

        Golden-SQL equality proves the integration chain
        (json.dumps → _escape → f-string) is wired correctly.
        """
        bridge, mock_http = bridge_and_mock
        evil_payload = {"skill_name": 'PRIME"; DROP TABLE execution_trace; --'}
        event = _evt(payload=evil_payload)

        await bridge._handle(event)

        sql = _last_sql(mock_http)
        expected = _expected_sql(bridge, event)
        assert sql == expected, (
            f"SQL mismatch (possible payload injection escape bug):\n"
            f"Got:      {sql!r}\n"
            f"Expected: {expected!r}"
        )

    async def test_payload_content_is_preserved_not_dropped(self, bridge_and_mock):
        """Payload content survives escaping — sanitize, never silently drop."""
        bridge, mock_http = bridge_and_mock
        event = _evt(payload={"key": DQUOTE + "; DROP TABLE x; --"})

        await bridge._handle(event)

        sql = _last_sql(mock_http)
        assert "DROP TABLE" in sql, "Payload content must be present in SQL (just escaped)"
        assert "key" in sql, "Payload key must be present"

    async def test_deeply_nested_payload_golden_sql(self, bridge_and_mock):
        """Nested dicts/lists with quotes are all captured via json.dumps + _escape."""
        bridge, mock_http = bridge_and_mock
        payload = {"a": {"b": [DQUOTE + "c" + DQUOTE, "normal"]}}
        event = _evt(payload=payload)

        await bridge._handle(event)

        assert _last_sql(mock_http) == _expected_sql(bridge, event)


# ── 3. SQL injection via source field ────────────────────────────────────────


class TestSourceSQLInjection:
    pytestmark = pytest.mark.asyncio
    """Adversarial: malicious source strings must not break the SQL source field."""

    async def test_embedded_quote_in_source_golden_sql(self, bridge_and_mock):
        """DISCRIMINATING (golden SQL): source with \\\" produces correct escaped SQL."""
        bridge, mock_http = bridge_and_mock
        event = _evt(source='attacker"; SELECT * FROM secrets; --')

        await bridge._handle(event)

        sql = _last_sql(mock_http)
        assert sql == _expected_sql(bridge, event), (
            f"SQL mismatch (source injection):\n"
            f"Got:      {sql!r}\n"
            f"Expected: {_expected_sql(bridge, event)!r}"
        )

    async def test_multiple_quotes_in_source(self, bridge_and_mock):
        """Multiple double-quotes in source are all escaped."""
        bridge, mock_http = bridge_and_mock
        event = _evt(source=DQUOTE + "a" + DQUOTE + "b" + DQUOTE)

        await bridge._handle(event)

        assert _last_sql(mock_http) == _expected_sql(bridge, event)

    async def test_backslash_in_source_doubled(self, bridge_and_mock):
        """Backslashes in source are doubled."""
        bridge, mock_http = bridge_and_mock
        event = _evt(source="path" + BACKSLASH + "file")

        await bridge._handle(event)

        assert _last_sql(mock_http) == _expected_sql(bridge, event)


# ── 4. Newline injection ──────────────────────────────────────────────────────


class TestNewlineInjection:
    pytestmark = pytest.mark.asyncio
    """Adversarial: newlines in payload or source must not appear raw in SQL."""

    async def test_newline_in_payload_eliminated_from_sql(self, bridge_and_mock):
        """DISCRIMINATING: literal \\n in payload value becomes \\\\n (not raw)."""
        bridge, mock_http = bridge_and_mock
        event = _evt(payload={"cmd": "safe" + NEWLINE + "DROP TABLE danger"})

        await bridge._handle(event)

        sql = _last_sql(mock_http)
        assert NEWLINE not in sql, f"Raw newline found in SQL: {sql!r}"
        assert "DROP TABLE" in sql, "Content must survive escaping (not be dropped)"

    async def test_newline_in_source_eliminated_from_sql(self, bridge_and_mock):
        """Newline in source field is also escaped."""
        bridge, mock_http = bridge_and_mock
        event = _evt(source="agent" + NEWLINE + "malicious; DROP TABLE foo;")

        await bridge._handle(event)

        sql = _last_sql(mock_http)
        assert NEWLINE not in sql, f"Raw newline in SQL from source field: {sql!r}"


# ── 5. replay_since edge cases ────────────────────────────────────────────────


class TestReplaySince:
    """Behavioral edge cases for replay_since."""

    def test_replay_since_zero_queries_all_events(self, bridge_and_mock):
        """replay_since(0.0) uses WHERE timestamp > 0.0 and returns decoded rows."""
        bridge, mock_http = bridge_and_mock
        mock_row = {
            "event_type": "DATA_PRODUCT_CREATED",
            "source": "producer",
            "timestamp": 100.0,
            "payload": '{"key": "val"}',
            "priority": 0,
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"result": [mock_row]}]
        mock_http.post.return_value = mock_resp

        result = bridge.replay_since(0.0)

        sql = _last_sql(mock_http)
        assert "WHERE timestamp > 0.0" in sql, f"Expected 'WHERE timestamp > 0.0' in: {sql!r}"
        assert len(result) == 1
        assert result[0]["event_type"] == "DATA_PRODUCT_CREATED"
        # JSON string payload should be decoded to dict
        assert result[0]["payload"] == {"key": "val"}

    def test_replay_since_far_future_returns_empty(self, bridge_and_mock):
        """replay_since(far future) with empty DB result returns []."""
        bridge, mock_http = bridge_and_mock
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"result": []}]
        mock_http.post.return_value = mock_resp

        result = bridge.replay_since(9999999999.9)

        sql = _last_sql(mock_http)
        assert "WHERE timestamp > 9999999999.9" in sql
        assert result == []

    def test_replay_since_malformed_json_payload_does_not_raise(self, bridge_and_mock):
        """DISCRIMINATING: malformed JSON payload in DB row leaves payload as-is; never raises.

        A fragile implementation would let json.JSONDecodeError propagate and crash
        the caller. The except clause must swallow it, leaving the raw string in place.
        """
        bridge, mock_http = bridge_and_mock
        malformed_row = {
            "event_type": "DATA_PRODUCT_UPDATED",
            "source": "producer",
            "timestamp": 500.0,
            "payload": "not-json{{{",
            "priority": 1,
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"result": [malformed_row]}]
        mock_http.post.return_value = mock_resp

        result = bridge.replay_since(0.0)  # must not raise

        assert len(result) == 1
        assert result[0]["payload"] == "not-json{{{", (
            "Malformed payload must be left as raw string, not replaced with {} or raised"
        )

    def test_replay_since_non_string_payload_does_not_raise(self, bridge_and_mock):
        """If DB row payload is already a dict (unexpected), passes through unchanged.

        json.loads(dict) raises TypeError — must be caught by the (JSONDecodeError,TypeError)
        guard in replay_since, leaving the row intact.
        """
        bridge, mock_http = bridge_and_mock
        dict_payload = {"already": "decoded"}
        mock_row = {
            "event_type": "LINEAGE_UPDATED",
            "source": "x",
            "timestamp": 200.0,
            "payload": dict_payload,
            "priority": 0,
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"result": [mock_row]}]
        mock_http.post.return_value = mock_resp

        result = bridge.replay_since(0.0)

        assert len(result) == 1
        assert result[0]["payload"] == dict_payload

    def test_replay_since_surreal_unreachable_returns_empty(self, bridge_and_mock):
        """DISCRIMINATING: SurrealDB HTTP failure during replay returns [] not raises."""
        bridge, mock_http = bridge_and_mock
        mock_http.post.side_effect = ConnectionRefusedError("SurrealDB down")

        result = bridge.replay_since(1000.0)

        assert result == [], "replay_since must return [] on HTTP failure, not raise"


# ── 6. Double-subscribe idempotency ──────────────────────────────────────────


class TestDoubleSubscribe:
    """Adversarial: calling subscribe() twice exposes a double-write design bug.

    This class DOCUMENTS the current behavior (2 writes per event on double-subscribe),
    intentionally not fixed so as to preserve the team lead's stated expected behavior.

    RECOMMENDED FIX (not applied):
        def subscribe(self, bus: EventBus) -> None:
            for event_type in self.SUBSCRIBED_TYPES:
                if self._handle not in bus._handlers[event_type]:
                    bus._handlers[event_type].append(self._handle)
    """

    @pytest.mark.asyncio
    async def test_double_subscribe_causes_two_writes_per_event(self, bridge_and_mock):
        """BUG DOCUMENTED: double subscribe() doubles SurrealDB writes for each event.

        subscribe() appends self._handle to bus._handlers[event_type] with no
        duplicate guard. A second call duplicates all 5 handler registrations.
        One DATA_PRODUCT_CREATED event then invokes _handle twice → 2 CREATE calls
        for a single logical event (data duplication).

        Current behavior: 2 writes. Correct behavior: 1 write.
        """
        bridge, mock_http = bridge_and_mock
        bus = EventBus()

        bridge.subscribe(bus)
        bridge.subscribe(bus)  # second call — no idempotency guard exists

        event = _evt(event_type=EventType.DATA_PRODUCT_CREATED)
        # Dispatch directly (bypass the async queue so we don't need to start/stop bus)
        await bus._dispatch(event)

        write_calls = mock_http.post.call_count
        assert write_calls == 2, (
            f"BUG CONFIRMED: double subscribe() caused {write_calls} SurrealDB writes "
            "for a single event (expected 2, documenting the double-write design bug). "
            "subscribe() lacks idempotency — each call duplicates handler registration."
        )

    def test_single_subscribe_registers_one_handler_per_event_type(self, bridge_and_mock):
        """Single subscribe() registers exactly one _handle per SUBSCRIBED_TYPE."""
        bridge, _ = bridge_and_mock
        bus = EventBus()
        bridge.subscribe(bus)

        for et in DataMeshEventBridge.SUBSCRIBED_TYPES:
            count = bus._handlers[et].count(bridge._handle)
            assert count == 1, f"Expected 1 handler for {et.name}, got {count}"

    def test_subscribe_covers_all_five_datamesh_event_types(self, bridge_and_mock):
        """subscribe() registers handlers for all 5 SUBSCRIBED_TYPES, not fewer."""
        bridge, _ = bridge_and_mock
        bus = EventBus()
        bridge.subscribe(bus)

        registered_types = {
            et for et in DataMeshEventBridge.SUBSCRIBED_TYPES if bridge._handle in bus._handlers[et]
        }
        assert registered_types == set(DataMeshEventBridge.SUBSCRIBED_TYPES), (
            f"Not all SUBSCRIBED_TYPES got handlers. Registered: {registered_types}"
        )


# ── 7. Write failure resilience ───────────────────────────────────────────────


class TestWriteFailureResilience:
    pytestmark = pytest.mark.asyncio
    """_handle must never propagate exceptions from SurrealDB write failures."""

    async def test_connection_refused_is_non_fatal(self, bridge_and_mock):
        """DISCRIMINATING: ConnectionRefusedError from httpx must not propagate."""
        bridge, mock_http = bridge_and_mock
        mock_http.post.side_effect = ConnectionRefusedError("SurrealDB unreachable")

        try:
            await bridge._handle(_evt())
        except Exception as exc:
            pytest.fail(
                f"_handle raised {type(exc).__name__}: {exc} — "
                "write failures must be non-fatal (caught and logged at DEBUG)"
            )

    async def test_timeout_error_is_non_fatal(self, bridge_and_mock):
        """httpx.TimeoutException must not propagate from _handle."""
        import httpx

        bridge, mock_http = bridge_and_mock
        mock_http.post.side_effect = httpx.TimeoutException("timed out")

        try:
            await bridge._handle(_evt())
        except Exception as exc:
            pytest.fail(f"_handle raised on timeout: {exc}")

    async def test_write_failure_logged_at_debug_not_warning(self, bridge_and_mock, caplog):
        """DISCRIMINATING: write failures log at DEBUG, NOT WARNING or ERROR.

        WARNING/ERROR for transient SurrealDB blips would spam operator logs
        for a deliberately non-fatal design.
        """
        bridge, mock_http = bridge_and_mock
        mock_http.post.side_effect = ConnectionRefusedError("no surreal")

        with caplog.at_level(logging.DEBUG, logger="cohezion.data_mesh.event_bridge"):
            await bridge._handle(_evt())

        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert debug_records, "Write failure must emit at least one DEBUG log"

        high_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert not high_records, (
            f"Write failure logged above DEBUG (operator noise): "
            f"{[(r.levelname, r.message) for r in high_records]}"
        )


# ── 8. BONUS: raw-interpolated timestamp / priority injection ─────────────────


class TestRawInterpolatedFieldInjection:
    pytestmark = pytest.mark.asyncio
    """BONUS adversarial: timestamp and priority are interpolated WITHOUT quoting.

    Event is a frozen dataclass with type annotations but NO runtime type enforcement.
    Constructing an Event with a string value for timestamp or priority injects SQL
    directly at statement level — unquoted, more dangerous than string-field injection.

    FIXED in this PR: _handle now casts ts = float(event.timestamp) and
    pri = int(event.priority) with a try/except guard; non-numeric events are
    dropped silently at DEBUG level rather than injecting or crashing.
    """

    async def test_string_timestamp_event_is_dropped_not_injected(self, bridge_and_mock):
        """FIXED: string value in timestamp field is rejected by float() guard.

        Before fix: f'timestamp = {event.timestamp}' with a string value produced
        an unquoted SQL injection (e.g. timestamp = 0; DROP TABLE foo; --).

        After fix: float("0; DROP TABLE...") raises ValueError, the event is
        dropped, and mock_http.post is never called.
        """
        bridge, mock_http = bridge_and_mock
        event = Event(
            type=EventType.DATA_PRODUCT_CREATED,
            source="attacker",
            timestamp="0; DROP TABLE injection_target; --",  # type: ignore[arg-type]
            payload={},
            priority=0,
        )

        await bridge._handle(event)

        assert mock_http.post.call_count == 0, (
            f"VULNERABILITY: event with non-float timestamp sent {mock_http.post.call_count} "
            "SQL statements to SurrealDB. Expected 0 (event should be dropped by guard)."
        )

    async def test_string_priority_event_is_dropped_not_injected(self, bridge_and_mock):
        """FIXED: string value in priority field is rejected by int() guard."""
        bridge, mock_http = bridge_and_mock
        event = Event(
            type=EventType.DATA_PRODUCT_CREATED,
            source="attacker",
            timestamp=1000.0,
            payload={},
            priority="0; DROP TABLE priority_target; --",  # type: ignore[arg-type]
        )

        await bridge._handle(event)

        assert mock_http.post.call_count == 0, (
            f"VULNERABILITY: event with non-int priority sent {mock_http.post.call_count} "
            "SQL statements to SurrealDB. Expected 0 (event should be dropped by guard)."
        )

    async def test_valid_numeric_types_still_write_normally(self, bridge_and_mock):
        """Guard must not discard legitimate events with correct numeric types."""
        bridge, mock_http = bridge_and_mock
        event = _evt(timestamp=1234.5, priority=7)

        await bridge._handle(event)

        assert mock_http.post.call_count == 1, (
            "Valid event (float timestamp, int priority) should write normally"
        )
        sql = _last_sql(mock_http)
        assert "timestamp = 1234.5" in sql
        assert "priority = 7" in sql

    async def test_integer_timestamp_accepted_by_guard(self, bridge_and_mock):
        """float() accepts int timestamps — no regression for integer timestamps."""
        bridge, mock_http = bridge_and_mock
        event = _evt(timestamp=1000, priority=0)  # int, not float

        await bridge._handle(event)

        assert mock_http.post.call_count == 1, "int timestamp is acceptable (float() casts it)"

    async def test_type_guard_logs_at_debug_on_rejection(self, bridge_and_mock, caplog):
        """DISCRIMINATING: rejected events (non-numeric fields) log at DEBUG."""
        bridge, mock_http = bridge_and_mock
        event = Event(
            type=EventType.DATA_PRODUCT_CREATED,
            source="x",
            timestamp="not-a-float",  # type: ignore[arg-type]
            payload={},
            priority=0,
        )

        with caplog.at_level(logging.DEBUG, logger="cohezion.data_mesh.event_bridge"):
            await bridge._handle(event)

        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert debug_records, (
            "Rejected event (bad timestamp) must emit a DEBUG log so operators "
            "can diagnose unexpected event drops."
        )
