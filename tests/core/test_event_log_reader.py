"""Discriminating tests for the unified event_log reader (2026-08-14).

The bus is split-brained: shell hooks + deepdive wrote ``event_log`` to db ``main``
(schema A: ``session``, ISO-string timestamps), while SurrealClient-based writers wrote
db ``vault`` (schema B: ``session_id``, epoch-float timestamps) — live-verified 434 rows
in main (frozen since 2026-08-03) vs 1,949 rows in vault (daemon writing minutes ago).
Nobody could see the whole bus. This reader normalizes both schemas from both databases
into one shape.

Each test fails a plausible wrong implementation:
- an impl that only reads one schema's field names → normalize tests
- an impl that assumes one timestamp type → epoch/ISO round-trip tests
- an impl that queries one db or doesn't merge-sort → fetch tests
- an impl that trusts payload to be a dict → payload coercion tests
"""

from __future__ import annotations

from unittest.mock import patch

from cohezion.core.event_log_reader import (
    NormalizedEvent,
    fetch_events,
    normalize_row,
)


class TestNormalizeRowSchemaA:
    """db=main shape: session, ISO-string timestamp, dict payload."""

    ROW = {
        "id": "event_log:evt_deepdive_coordinator_1785731716733",
        "type": "AGENT_COMPLETE",
        "source": "deepdive.deepdive_coordinator",
        "session": "deep-dive-dogfood-session",
        "timestamp": "2026-08-03T04:35:16.733577+00:00",
        "payload": {"spec_file": "/x/y.md"},
    }

    def test_session_read_from_session_field(self) -> None:
        ev = normalize_row(self.ROW, origin_db="main")
        assert ev.session == "deep-dive-dogfood-session"

    def test_iso_timestamp_parsed_to_epoch(self) -> None:
        ev = normalize_row(self.ROW, origin_db="main")
        # 2026-08-03T04:35:16.733577+00:00 == epoch 1785731716.733577
        assert abs(ev.epoch - 1785731716.733577) < 0.001

    def test_type_and_origin_preserved(self) -> None:
        ev = normalize_row(self.ROW, origin_db="main")
        assert ev.type == "AGENT_COMPLETE"
        assert ev.origin_db == "main"


class TestNormalizeRowSchemaB:
    """db=vault shape: session_id, epoch-float timestamp, priority."""

    ROW = {
        "id": "event_log:evt_s-77b9f9d6a892_1786586816533_403867",
        "type": "AGENT_START",
        "source": "claude-code.session",
        "session_id": "s-77b9f9d6a892",
        "timestamp": 1786586816.533047,
        "priority": 0,
        "payload": {"branch": "feat/compound-session-20260812"},
        "valid_from": "2026-08-13T02:06:56Z",
    }

    def test_session_read_from_session_id_field(self) -> None:
        """Discriminating: an impl reading only 'session' returns '' here."""
        ev = normalize_row(self.ROW, origin_db="vault")
        assert ev.session == "s-77b9f9d6a892"

    def test_float_epoch_passes_through(self) -> None:
        ev = normalize_row(self.ROW, origin_db="vault")
        assert abs(ev.epoch - 1786586816.533047) < 0.001

    def test_iso_derived_from_epoch(self) -> None:
        ev = normalize_row(self.ROW, origin_db="vault")
        assert ev.iso.startswith("2026-08-1")  # UTC date of that epoch


class TestNormalizeRowEdgeShapes:
    def test_event_type_field_variant(self) -> None:
        """data_product_event-style rows use 'event_type', not 'type'."""
        ev = normalize_row(
            {"id": "x:1", "event_type": "data_product_created", "timestamp": 1786000000.0},
            origin_db="main",
        )
        assert ev.type == "data_product_created"

    def test_numeric_string_timestamp(self) -> None:
        """Some writers stringify the epoch float."""
        ev = normalize_row({"id": "x:2", "timestamp": "1786706806.2520914"}, origin_db="vault")
        assert abs(ev.epoch - 1786706806.2520914) < 0.001

    def test_string_payload_coerced_via_json(self) -> None:
        """research_products-style writers store payload as an escaped JSON string."""
        ev = normalize_row({"id": "x:3", "timestamp": 1.0, "payload": '{"a": 1}'}, origin_db="main")
        assert ev.payload == {"a": 1}

    def test_garbage_payload_wrapped_not_crashed(self) -> None:
        ev = normalize_row({"id": "x:4", "timestamp": 1.0, "payload": "not json"}, origin_db="main")
        assert ev.payload == {"raw": "not json"}

    def test_missing_everything_is_survivable(self) -> None:
        ev = normalize_row({}, origin_db="vault")
        assert ev.type == "UNKNOWN"
        assert ev.session == ""
        assert ev.epoch == 0.0


class TestFetchEventsMergesBothDatabases:
    MAIN_ROW = {
        "id": "event_log:a",
        "type": "AGENT_COMPLETE",
        "session": "old-session",
        "timestamp": "2026-08-03T04:35:16+00:00",
        "payload": {},
    }
    VAULT_ROW = {
        "id": "event_log:b",
        "type": "CUSTOM",
        "session_id": "daemon",
        "timestamp": 1786706806.25,
        "payload": {},
    }

    def _mock_sql(self, responses: dict[str, list[dict]]):
        def fake(db: str, query: str, timeout: float = 10.0) -> list[dict]:
            return responses.get(db, [])

        return patch("cohezion.core.event_log_reader._sql", side_effect=fake)

    def test_queries_both_dbs_and_merges_sorted_desc(self) -> None:
        """Discriminating: a one-db impl returns 1 row; an unsorted impl misorders."""
        with self._mock_sql({"main": [self.MAIN_ROW], "vault": [self.VAULT_ROW]}):
            events = fetch_events(limit=10)
        assert len(events) == 2
        assert events[0].id == "event_log:b"  # 2026-08-14 epoch > 2026-08-03 epoch
        assert {e.origin_db for e in events} == {"main", "vault"}

    def test_limit_applied_after_merge(self) -> None:
        with self._mock_sql({"main": [self.MAIN_ROW], "vault": [self.VAULT_ROW]}):
            events = fetch_events(limit=1)
        assert len(events) == 1
        assert events[0].id == "event_log:b"  # newest survives the cut, not db-order luck

    def test_session_filter_matches_both_schema_field_names(self) -> None:
        """Discriminating: filtering must act on the NORMALIZED session, so it finds
        rows regardless of which raw field the writer used."""
        with self._mock_sql({"main": [self.MAIN_ROW], "vault": [self.VAULT_ROW]}):
            events = fetch_events(limit=10, session="daemon")
        assert [e.id for e in events] == ["event_log:b"]

    def test_since_epoch_filter(self) -> None:
        with self._mock_sql({"main": [self.MAIN_ROW], "vault": [self.VAULT_ROW]}):
            events = fetch_events(limit=10, since_epoch=1786000000.0)
        assert [e.id for e in events] == ["event_log:b"]

    def test_fetch_window_partitioned_by_timestamp_type(self) -> None:
        """Discriminating (cloud-review finding, 2026-08-14): a single server-side
        ORDER BY over MIXED timestamp types returns an arbitrary window — 23 old
        ISO-string rows shadowed 505 live float rows in db=main, and client-side
        sorting cannot recover rows never fetched. Each db must be fetched as TWO
        per-type partitions (within a type, ordering is consistent), each with its
        own ORDER BY ... LIMIT."""
        captured: list[str] = []

        def fake(db: str, query: str, timeout: float = 10.0) -> list[dict]:
            captured.append(query)
            return []

        with patch("cohezion.core.event_log_reader._sql", side_effect=fake):
            fetch_events(limit=10)
        number_qs = [q for q in captured if "type::is_number(timestamp)" in q]
        string_qs = [q for q in captured if "type::is_string(timestamp)" in q]
        assert len(number_qs) == 2 and len(string_qs) == 2, (
            f"expected one number- and one string-partition query per db, got: {captured}"
        )
        for q in captured:
            assert "ORDER BY timestamp DESC" in q and "LIMIT" in q

    def test_rows_from_both_partitions_merged(self) -> None:
        """A shadowed-partition row (float-stamped, newer) must win over the
        string-partition row even though the string partition also returns rows."""

        def fake(db: str, query: str, timeout: float = 10.0) -> list[dict]:
            if db != "main":
                return []
            if "type::is_number" in query:
                return [
                    {
                        "id": "event_log:new",
                        "type": "SYSTEM_HEALTH",
                        "session": "live",
                        "timestamp": 1786738492.2,
                        "payload": {},
                    }
                ]
            return [self.MAIN_ROW]  # the old ISO-stamped row

        with patch("cohezion.core.event_log_reader._sql", side_effect=fake):
            events = fetch_events(limit=10, dbs=("main",))
        assert [e.id for e in events][:1] == ["event_log:new"]
        assert len(events) == 2

    def test_session_filter_pushed_into_sql_where_on_both_field_names(self) -> None:
        """Discriminating: a client-side-only filter over a shallow window silently
        misses rows older than the window (live-caught with this session's own day-1
        AGENT_START). The WHERE must name BOTH raw field variants."""
        captured: list[str] = []

        def fake(db: str, query: str, timeout: float = 10.0) -> list[dict]:
            captured.append(query)
            return []

        with patch("cohezion.core.event_log_reader._sql", side_effect=fake):
            fetch_events(limit=10, session="daemon")
        assert captured, "no SQL issued"
        for q in captured:
            assert "session = 'daemon'" in q and "session_id = 'daemon'" in q

    def test_unsafe_filter_value_rejected_before_any_sql(self) -> None:
        """Discriminating: string-interpolated filters must refuse injection shapes
        (M5 pattern) rather than pass them into SurrealQL."""
        with patch("cohezion.core.event_log_reader._sql") as mock_sql:
            try:
                fetch_events(limit=10, session="x' OR 1=1 --")
            except ValueError:
                pass
            else:
                raise AssertionError("injection-shaped session value must raise ValueError")
        assert not mock_sql.called

    def test_since_epoch_stays_client_side(self) -> None:
        """Mixed timestamp types in event_log make server-side time predicates lie —
        the query must NOT contain a timestamp comparison."""
        captured: list[str] = []

        def fake(db: str, query: str, timeout: float = 10.0) -> list[dict]:
            captured.append(query)
            return [self.VAULT_ROW]

        with patch("cohezion.core.event_log_reader._sql", side_effect=fake):
            fetch_events(limit=10, since_epoch=1786000000.0)
        for q in captured:
            assert "timestamp >" not in q and "timestamp <" not in q

    def test_one_db_down_does_not_lose_the_other(self) -> None:
        """Discriminating: a fail-closed impl returns [] when either db errors."""

        def fake(db: str, query: str, timeout: float = 10.0) -> list[dict]:
            if db == "main":
                raise ConnectionError("db main unreachable")
            return [self.VAULT_ROW]

        with patch("cohezion.core.event_log_reader._sql", side_effect=fake):
            events = fetch_events(limit=10)
        assert [e.id for e in events] == ["event_log:b"]


class TestNormalizedEventRendering:
    def test_one_line_render_contains_the_essentials(self) -> None:
        ev = NormalizedEvent(
            id="event_log:x",
            type="AGENT_START",
            source="claude-code.session",
            session="s-abc",
            epoch=1786586816.5,
            iso="2026-08-13T02:06:56Z",
            payload={"branch": "b"},
            priority=None,
            origin_db="vault",
        )
        line = ev.render_line()
        for token in ("AGENT_START", "s-abc", "vault", "claude-code.session"):
            assert token in line
