"""SurrealClient must not stay on InMemoryStore forever after one failed startup connect."""

import asyncio
from unittest.mock import patch

import pytest

from cohezion.core.persistence import surreal_client as sc


class _Breaker:
    def allow_request(self) -> bool:
        return True

    def record_success(self) -> None:
        pass

    def record_failure(self) -> None:
        pass


class _FakeSurreal:
    """Stands in for surrealdb.AsyncSurreal; `up` is flipped by the test."""

    up = False

    def __init__(self, url: str) -> None:
        self.url = url

    async def connect(self) -> None:
        if not _FakeSurreal.up:
            raise OSError("server rejected WebSocket connection: HTTP 404")

    async def signin(self, creds: dict) -> None:
        pass

    async def use(self, ns: str, db: str) -> None:
        pass

    async def query(self, sql: str, params: dict | None = None):
        return [{"result": [{"ok": 1}]}]

    async def close(self) -> None:
        pass


@pytest.fixture
def fake_db(monkeypatch):
    _FakeSurreal.up = False
    monkeypatch.setattr(sc, "_FALLBACK_RETRY_BASE_S", 0.01)
    with (
        patch("surrealdb.AsyncSurreal", _FakeSurreal),
        patch.object(sc, "get_circuit", lambda *a, **k: _Breaker()),
        patch.object(sc, "_resolve_surreal_credentials", lambda: ("u", "p")),
    ):
        yield _FakeSurreal
    sc._FALLBACK_CLIENTS.clear()


@pytest.mark.asyncio
async def test_fallback_is_visible_then_recovers(fake_db):
    client = sc.SurrealClient()
    assert await client.connect() is True
    assert client.persistence_state == "fallback"
    assert sc.persistence_status()["in_memory_fallback"] is True

    fake_db.up = True
    await asyncio.sleep(0.05)  # past the first backoff deadline
    await client.query("SELECT 1")

    assert client.persistence_state == "connected"
    assert not isinstance(client._client, sc.InMemoryStore)
    assert sc.persistence_status()["in_memory_fallback"] is False


@pytest.mark.asyncio
async def test_no_retry_before_backoff_deadline(fake_db, monkeypatch):
    monkeypatch.setattr(sc, "_FALLBACK_RETRY_BASE_S", 60.0)
    client = sc.SurrealClient()
    await client.connect()
    fake_db.up = True
    await client.query("SELECT 1")  # deadline is 60 s away: must stay on memory
    assert client.persistence_state == "fallback"


@pytest.mark.asyncio
async def test_failed_retry_stays_in_fallback_and_backs_off(fake_db):
    client = sc.SurrealClient()
    await client.connect()
    await asyncio.sleep(0.05)
    await client.query("SELECT 1")  # retry fails: server still down
    assert client.persistence_state == "fallback"
    assert client._fallback_failures == 2
    assert client._fallback_delay() >= 0.04
