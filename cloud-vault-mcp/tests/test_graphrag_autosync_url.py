"""GraphRAGAutoSync must hand the configured SurrealDB URL to its importer."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_server import graphrag_autosync as ga


class _Importer:
    seen: dict = {}

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


def test_default_leaves_importer_default():
    _start()
    assert _Importer.seen == {}
