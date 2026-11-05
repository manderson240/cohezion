"""Broadcast age cap on SessionBus._pending (2026-11-05).

Acks are per session, so without a bound every new session id inherited the whole
broadcast backlog through ~/.claude/hooks/session-inbox.sh. Broadcasts (to_session 'all'
or 'ALL') older than COHEZION_BUS_BROADCAST_MAX_AGE_H (default 72h) are not delivered;
direct messages are never aged out.

Two layers:
- Hermetic: capture the generated SurrealQL (runs in CI).
- Behavioural: run the real query against a THROWAWAY database on :8001 (never `main`),
  skipped when SurrealDB is unreachable. Only this layer proves the predicate filters rows.
"""

from __future__ import annotations

import base64
import json
import urllib.request
import uuid

import pytest

from cohezion.sessions import session_bus
from cohezion.sessions.session_bus import MessageKind, SessionBus


ENV = session_bus._BROADCAST_MAX_AGE_ENV


# --- hermetic: the query shape -------------------------------------------------------


@pytest.fixture
def captured(monkeypatch):
    queries: list[str] = []
    monkeypatch.setattr(session_bus, "_sql", lambda q, timeout=5.0: queries.append(q) or [])
    return queries


def test_default_bound_is_72h_inside_where(captured, monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    SessionBus()._pending("s-abc", MessageKind.MSG)
    q = captured[0]
    assert "created_at > time::now() - 259200s" in q
    # The bound must precede ORDER BY/LIMIT, or the 50 oldest stale rows still win.
    assert q.index("259200s") < q.index("ORDER BY")


def test_uppercase_all_is_matched(captured, monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    SessionBus()._pending("s-abc", MessageKind.MSG)
    assert '["all", "ALL"]' in captured[0]


def test_direct_message_branch_is_unbounded(captured):
    SessionBus()._pending("s-abc", MessageKind.MSG)
    assert 'to_session = "s-abc" OR (to_session IN' in captured[0]


@pytest.mark.parametrize(("raw", "seconds"), [("6", 21600), ("0.5", 1800)])
def test_env_overrides_bound(captured, monkeypatch, raw, seconds):
    monkeypatch.setenv(ENV, raw)
    SessionBus()._pending("s-abc", MessageKind.MSG)
    assert f"time::now() - {seconds}s" in captured[0]


@pytest.mark.parametrize("raw", ["garbage", "nan", "-5", "0", ""])
def test_bad_env_falls_back_to_default(captured, monkeypatch, raw):
    monkeypatch.setenv(ENV, raw)
    SessionBus()._pending("s-abc", MessageKind.MSG)
    assert "259200s" in captured[0]


@pytest.mark.parametrize("raw", ["1e15", "1e300", "876001"])
def test_huge_finite_env_is_unbounded_not_an_overflow(captured, monkeypatch, raw):
    # A duration this large makes SurrealDB ERR, which _sql reads as no-rows, silently
    # dropping DIRECT messages too. It must take the unbounded branch instead.
    monkeypatch.setenv(ENV, raw)
    SessionBus()._pending("s-abc", MessageKind.MSG)
    assert "created_at >" not in captured[0]


def test_tiny_env_never_rounds_to_zero_seconds(captured, monkeypatch):
    monkeypatch.setenv(ENV, "0.00001")
    SessionBus()._pending("s-abc", MessageKind.MSG)
    assert "time::now() - 1s" in captured[0]


@pytest.mark.parametrize("addr", ["All", " ALL ", "all"])
def test_post_normalises_broadcast_address(captured, addr):
    SessionBus().post(addr, "x")
    assert 'to_session = "all"' in captured[0]


def test_inf_removes_the_bound(captured, monkeypatch):
    monkeypatch.setenv(ENV, "inf")
    SessionBus()._pending("s-abc", MessageKind.MSG)
    assert "created_at >" not in captured[0]


# --- behavioural: the predicate against a real SurrealDB -----------------------------


def _surreal_up() -> bool:
    try:
        url = "http://localhost:8001/health"
        with urllib.request.urlopen(url, timeout=1.0) as r:
            return r.status == 200
    except Exception:
        return False


live = pytest.mark.skipif(not _surreal_up(), reason="SurrealDB :8001 not reachable")


def _ns_sql(query: str) -> None:
    """Namespace-level statement (no db header): DEFINE/REMOVE the throwaway database."""
    req = urllib.request.Request(  # noqa: S310 - constant localhost URL
        session_bus.SURREAL_URL,
        data=query.encode(),
        headers={
            "surreal-ns": session_bus._NS,
            "Accept": "application/json",
            "Authorization": "Basic " + base64.b64encode(session_bus._AUTH.encode()).decode(),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5.0) as r:  # noqa: S310
        batches = json.loads(r.read())
    assert all(b.get("status") == "OK" for b in batches), batches


@pytest.fixture
def throwaway_db(monkeypatch):
    name = f"test_scp_agecap_{uuid.uuid4().hex[:12]}"
    assert name.startswith("test_scp_agecap_")  # never main
    _ns_sql(f"DEFINE DATABASE {name};")
    monkeypatch.setattr(session_bus, "_DB", name)
    monkeypatch.delenv(ENV, raising=False)
    try:
        yield name
    finally:
        _ns_sql(f"REMOVE DATABASE IF EXISTS {name};")


def _insert(to_session: str, body: str, age_h: float | None, kind: str = "MSG") -> None:
    created = "" if age_h is None else f", created_at = time::now() - {int(age_h * 3600)}s"
    rows = session_bus._sql(
        f"CREATE session_bus SET to_session = {json.dumps(to_session)}, from_session = 't', "
        f"kind = {json.dumps(kind)}, body = {json.dumps(body)}, acked_by = [], "
        f"claimed_by = []{created};"
    )
    assert rows, "insert did not land: an empty-result test would pass vacuously"


def _bodies(sid: str, kind: MessageKind = MessageKind.MSG) -> set[str]:
    return {r["body"] for r in SessionBus()._pending(sid, kind)}


@live
def test_live_old_broadcast_not_delivered_to_new_sid(throwaway_db):
    _insert("all", "old-broadcast", age_h=100)
    _insert("ALL", "old-ALL", age_h=100)
    assert _bodies("s-newsid") == set()


@live
def test_live_fresh_broadcast_delivered(throwaway_db):
    _insert("all", "fresh-broadcast", age_h=1)
    _insert("ALL", "fresh-ALL", age_h=1)
    assert _bodies("s-newsid") == {"fresh-broadcast", "fresh-ALL"}


@live
def test_live_old_direct_message_still_delivered(throwaway_db):
    _insert("s-newsid", "old-direct", age_h=1000)
    _insert("all", "old-broadcast", age_h=100)
    assert _bodies("s-newsid") == {"old-direct"}


@live
def test_live_discriminating_inf_redelivers_old_broadcast(throwaway_db, monkeypatch):
    _insert("all", "old-broadcast", age_h=100)
    assert _bodies("s-newsid") == set()  # bounded: hidden
    monkeypatch.setenv(ENV, "inf")
    assert _bodies("s-newsid") == {"old-broadcast"}  # bound neutralised: back


@live
def test_live_fresh_broadcast_not_starved_by_stale_backlog(throwaway_db):
    # 60 stale rows exceed LIMIT 50: only an in-WHERE filter lets the fresh one through.
    for i in range(60):
        _insert("all", f"stale-{i}", age_h=100 + i)
    _insert("all", "fresh-broadcast", age_h=1)
    assert _bodies("s-newsid") == {"fresh-broadcast"}


@live
def test_live_fetch_acks_and_does_not_redeliver(throwaway_db):
    _insert("all", "fresh-broadcast", age_h=1)
    assert [r["body"] for r in SessionBus().fetch("s-newsid")] == ["fresh-broadcast"]
    assert SessionBus().fetch("s-newsid") == []


@live
def test_live_boundary_71h_delivered_73h_not(throwaway_db):
    _insert("all", "at-71h", age_h=71)
    _insert("all", "at-73h", age_h=73)
    assert _bodies("s-newsid") == {"at-71h"}


@live
def test_live_huge_env_keeps_direct_messages(throwaway_db, monkeypatch):
    _insert("s-newsid", "direct", age_h=1)
    monkeypatch.setenv(ENV, "1e15")
    assert _bodies("s-newsid") == {"direct"}


@live
def test_live_broadcast_without_created_at_is_dropped(throwaway_db):
    _insert("all", "no-timestamp", age_h=None)
    _insert("s-newsid", "direct-no-timestamp", age_h=None)
    assert _bodies("s-newsid") == {"direct-no-timestamp"}


@live
def test_live_reply_broadcasts_are_aged_too(throwaway_db):
    _insert("all", "old-reply", age_h=100, kind="REPLY")
    _insert("ALL", "fresh-reply", age_h=1, kind="REPLY")
    assert _bodies("s-newsid", MessageKind.REPLY) == {"fresh-reply"}
