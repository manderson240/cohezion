"""Hardening of SurrealClient's fallback/retry path (operator-map defects F1-F6, B1)."""

import asyncio
import logging
import sys
import time
from unittest.mock import patch

import pytest

from cohezion.core.persistence import surreal_client as sc


class _Breaker:
    open_ = False

    def allow_request(self) -> bool:
        return not _Breaker.open_

    def record_success(self) -> None:
        pass

    def record_failure(self) -> None:
        pass


class _Fake:
    """Stands in for surrealdb.AsyncSurreal. Behaviour is steered through class attributes."""

    instances: list["_Fake"] = []
    connect_impl = None  # async callable(self) or None for instant success
    signin_error: Exception | None = None

    def __init__(self, url: str) -> None:
        self.url = url
        self.closed = 0
        _Fake.instances.append(self)

    async def connect(self) -> None:
        if _Fake.connect_impl is not None:
            await _Fake.connect_impl(self)

    async def signin(self, creds: dict) -> None:
        if _Fake.signin_error is not None:
            raise _Fake.signin_error

    async def use(self, ns: str, db: str) -> None:
        pass

    async def query(self, sql: str, params: dict | None = None):
        return [{"real": True}]

    async def create(self, table: str, data: dict):
        return [{"real": True}]

    async def close(self) -> None:
        self.closed += 1


@pytest.fixture
def fake_db(monkeypatch):
    _Fake.instances = []
    _Fake.connect_impl = None
    _Fake.signin_error = None
    _Breaker.open_ = False
    monkeypatch.setattr(sc, "_FALLBACK_RETRY_BASE_S", 0.01)
    monkeypatch.setattr(sc, "_SHARED_STORE", None)
    with (
        patch("surrealdb.AsyncSurreal", _Fake),
        patch.object(sc, "get_circuit", lambda *a, **k: _Breaker()),
        patch.object(sc, "_resolve_surreal_credentials", lambda: ("u", "p")),
    ):
        yield _Fake
    sc._FALLBACK_CLIENTS.clear()


async def _never(self) -> None:
    await asyncio.sleep(3600)


# --- F1: a wedged server must not hold a fallback caller -------------------------------------


@pytest.mark.asyncio
async def test_f1_wedged_server_does_not_block_fallback_operation(fake_db, monkeypatch):
    client = sc.SurrealClient()
    await client.connect()  # refused-style start: use the fallback
    assert client.persistence_state == "connected"  # instant success; now force fallback
    client._use_fallback()
    fake_db.connect_impl = _never
    monkeypatch.setattr(sc, "_FALLBACK_RETRY_TIMEOUT_S", 0.1)
    client._fallback_retry_at = 0.0
    t0 = time.monotonic()
    await asyncio.wait_for(client.create("t", {"id": "a"}), 5)
    assert time.monotonic() - t0 < 2.0
    assert client.persistence_state == "fallback"


@pytest.mark.asyncio
async def test_f1_initial_connect_is_also_bounded(fake_db, monkeypatch):
    fake_db.connect_impl = _never
    monkeypatch.setattr(sc, "_CONNECT_TIMEOUT_S", 0.1)
    client = sc.SurrealClient()
    await asyncio.wait_for(client.connect(), 5)
    assert client.persistence_state == "fallback"


# --- F3: every failed handshake is closed ----------------------------------------------------


@pytest.mark.asyncio
async def test_f3_rejected_signin_closes_the_half_open_client(fake_db):
    fake_db.signin_error = RuntimeError("signin rejected")
    client = sc.SurrealClient()
    await client.connect()
    for _ in range(3):
        client._fallback_retry_at = 0.0
        await client.query("SELECT 1")
    assert len(fake_db.instances) == 4
    assert all(i.closed == 1 for i in fake_db.instances)


@pytest.mark.asyncio
async def test_f3_timed_out_handshake_is_closed(fake_db, monkeypatch):
    fake_db.connect_impl = _never
    monkeypatch.setattr(sc, "_CONNECT_TIMEOUT_S", 0.05)
    client = sc.SurrealClient()
    await client.connect()
    assert [i.closed for i in fake_db.instances] == [1]


@pytest.mark.asyncio
async def test_f3_real_library_wedged_server_leaves_no_socket_or_task(monkeypatch):
    """Un-faked AsyncSurreal against a websocket server that accepts and never answers."""
    websockets = pytest.importorskip("websockets")
    monkeypatch.setattr(sc, "_CONNECT_TIMEOUT_S", 0.3)
    monkeypatch.setattr(sc, "_resolve_surreal_credentials", lambda: ("u", "p"))
    conns = []

    async def handler(ws):
        conns.append(ws)
        async for _ in ws:
            pass

    async with websockets.serve(handler, "127.0.0.1", 0, subprotocols=["cbor"]) as srv:
        port = srv.sockets[0].getsockname()[1]
        before = len(asyncio.all_tasks())
        with patch.object(sc, "get_circuit", lambda *a, **k: _Breaker()):
            client = sc.SurrealClient(url=f"ws://127.0.0.1:{port}/rpc")
            await asyncio.wait_for(client.connect(), 5)
        assert client.persistence_state == "fallback"
        await asyncio.sleep(0.2)
        assert len(conns) == 1
        assert conns[0].state.name == "CLOSED"  # server saw the client hang up
        assert len(asyncio.all_tasks()) <= before + 1  # no leaked _recv_task / keepalive
    sc._FALLBACK_CLIENTS.clear()


# --- F4: one attempt in flight; a stale failure cannot undo recovery -------------------------


@pytest.mark.asyncio
async def test_f4_second_retry_does_not_overlap_a_slow_first(fake_db, monkeypatch):
    client = sc.SurrealClient()
    await client.connect()
    client._use_fallback()
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow(self) -> None:
        started.set()
        await release.wait()

    fake_db.connect_impl = slow
    monkeypatch.setattr(sc, "_FALLBACK_RETRY_TIMEOUT_S", 30)
    n_before = len(fake_db.instances)
    client._fallback_retry_at = 0.0
    first = asyncio.create_task(client.query("SELECT 1"))
    await started.wait()
    client._fallback_retry_at = 0.0  # backoff elapsed again while attempt 1 is in flight
    await asyncio.wait_for(client.query("SELECT 1"), 2)  # must not wait, must not start another
    assert len(fake_db.instances) == n_before + 1
    release.set()
    await first
    assert client.persistence_state == "connected"


@pytest.mark.asyncio
async def test_f4_stale_failure_cannot_override_recovered_client(fake_db, monkeypatch):
    client = sc.SurrealClient()
    await client.connect()
    client._use_fallback()
    monkeypatch.setattr(sc, "_FALLBACK_RETRY_TIMEOUT_S", 30)
    calls = 0
    gate = asyncio.Event()
    started = asyncio.Event()

    async def first_fails_late(self) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            started.set()
            await gate.wait()
            raise OSError("late failure")

    fake_db.connect_impl = first_fails_late
    n_before = len(fake_db.instances)
    client._fallback_retry_at = 0.0
    first = asyncio.create_task(client.query("SELECT 1"))
    await started.wait()
    second = asyncio.create_task(client.connect())  # a recovery attempt arrives meanwhile
    await asyncio.sleep(0.05)
    gate.set()
    await first
    await asyncio.wait_for(second, 2)
    assert client.persistence_state == "connected"
    assert not isinstance(client._client, sc.InMemoryStore)
    assert all(i.closed == 1 for i in fake_db.instances[n_before:] if i is not client._client)


# --- F2: fallback retry never raises the credential error; first connect stays strict ---------


@pytest.mark.asyncio
async def test_f2_retry_without_credentials_does_not_raise(fake_db, caplog):
    def refuse():
        raise sc.InsecureSurrealCredentialsError("no creds")

    _Breaker.open_ = True
    client = sc.SurrealClient()
    await client.connect()  # breaker open: fallback without resolving credentials
    assert client.persistence_state == "fallback"
    _Breaker.open_ = False
    with patch.object(sc, "_resolve_surreal_credentials", refuse):
        await asyncio.sleep(0.02)
        with caplog.at_level(logging.WARNING, logger=sc.logger.name):
            r = await client.create("t", {"id": "b"})
            await asyncio.sleep(0.02 * 2**client._fallback_failures)
            await client.create("t", {"id": "c"})
    assert r
    assert client.persistence_state == "fallback"
    assert sum("cannot proceed: no secure credentials" in m for m in caplog.messages) == 1


@pytest.mark.asyncio
async def test_f2_initial_connect_without_credentials_still_raises(fake_db):
    def refuse():
        raise sc.InsecureSurrealCredentialsError("no creds")

    with patch.object(sc, "_resolve_surreal_credentials", refuse):
        with pytest.raises(sc.InsecureSurrealCredentialsError):
            await sc.SurrealClient().connect()
        with pytest.raises(sc.InsecureSurrealCredentialsError):
            await sc.SurrealClient().query("SELECT 1")  # first use is an initial connect too


# --- F5: a missing surrealdb package is a fallback, and says so ------------------------------


@pytest.mark.asyncio
async def test_f5_import_failure_is_reported_as_fallback(fake_db, monkeypatch):
    monkeypatch.setitem(sys.modules, "surrealdb", None)  # `from surrealdb import X` -> ImportError
    client = sc.SurrealClient()
    await client.connect()
    assert isinstance(client._client, sc.InMemoryStore)
    assert client.persistence_state == "fallback"
    assert sc.persistence_status()["clients_in_fallback"] == 1


# --- F6: unreplayed fallback writes are announced at recovery --------------------------------


@pytest.mark.asyncio
async def test_f6_recovery_warns_about_unreplayed_writes(fake_db, caplog):
    fake_db.connect_impl = _raise_os
    client = sc.SurrealClient()
    await client.connect()
    assert client.persistence_state == "fallback"
    await client.create("t", {"id": "a"})
    await client.create("t", {"id": "b"})
    fake_db.connect_impl = None
    await asyncio.sleep(0.05)
    with caplog.at_level(logging.WARNING, logger=sc.logger.name):
        await client.query("SELECT 1")
    assert client.persistence_state == "connected"
    msgs = [m for m in caplog.messages if "NOT replayed" in m]
    assert len(msgs) == 1 and "2 write(s)" in msgs[0]


async def _raise_os(self=None):
    raise OSError("down")


@pytest.mark.asyncio
async def test_f6_clean_recovery_does_not_warn(fake_db, caplog):
    fake_db.connect_impl = _raise_os
    client = sc.SurrealClient()
    await client.connect()
    fake_db.connect_impl = None
    await asyncio.sleep(0.05)
    with caplog.at_level(logging.WARNING, logger=sc.logger.name):
        await client.query("SELECT 1")
    assert not [m for m in caplog.messages if "NOT replayed" in m]


# --- B1: the process-local registry is labelled, and tests cannot leak into each other -------

_LEAKED = []


@pytest.mark.asyncio
async def test_b1_a_leaves_a_client_in_fallback(fake_db):
    c = sc.SurrealClient()
    c._use_fallback()
    _LEAKED.append(c)  # strong ref: survives until the next test, like a leaked fixture
    assert sc.persistence_status()["clients_in_fallback"] == 1


def test_b1_b_registry_starts_empty_for_every_test():
    assert _LEAKED, "ordering precondition: the previous test must have run in this process"
    assert sc.persistence_status()["clients_in_fallback"] == 0


def test_b1_status_is_labelled_process_local():
    assert sc.persistence_status()["scope"] == "this_process_only"
