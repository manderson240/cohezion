"""GraphRAGAutoSync must hand the configured SurrealDB URL to its importer."""

import asyncio
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock, patch

from mcp_server import graphrag_autosync as ga


class _Importer:
    seen: ClassVar[dict] = {}

    def __init__(self, vault_path, **kwargs):
        _Importer.seen = kwargs

    async def __aenter__(self):
        return self


def _start(**kw):
    watcher = MagicMock()
    sync = ga.GraphRAGAutoSync(Path("."), watcher, **kw)

    async def run():
        with patch.object(ga, "GraphRAGImporter", _Importer):
            await sync.start()
            sync.task.cancel()

    asyncio.run(run())


def test_configured_surrealdb_url_reaches_the_importer():
    _start(surrealdb_url="http://example.invalid:9999")
    assert _Importer.seen == {"surrealdb_url": "http://example.invalid:9999"}


def test_no_argument_resolves_from_surrealdb_url_env(monkeypatch):
    monkeypatch.setenv("SURREALDB_URL", "http://env.invalid:7777")
    _start()
    assert _Importer.seen == {"surrealdb_url": "http://env.invalid:7777"}


def test_no_argument_no_env_uses_config_default(monkeypatch):
    monkeypatch.delenv("SURREALDB_URL", raising=False)
    _start()
    assert _Importer.seen == {"surrealdb_url": "http://localhost:8001"}
