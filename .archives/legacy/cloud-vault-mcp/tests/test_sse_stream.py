"""Tests for VaultEventStream SSE endpoint."""

import asyncio
import json

from mcp_server.sse_stream import VaultEventStream
from mcp_server.vault_watcher import VaultEvent


class MockWatcher:
    """Mock watcher that lets tests push events directly."""

    def __init__(self):
        self._queues: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._queues:
            self._queues.remove(q)

    async def push_event(self, event: VaultEvent) -> None:
        for q in self._queues:
            await q.put(event)

    @property
    def subscriber_count(self) -> int:
        return len(self._queues)


class TestVaultEventStream:
    async def test_event_format(self):
        """SSE output should have correct event: and data: lines."""
        watcher = MockWatcher()
        stream = VaultEventStream(watcher, heartbeat_seconds=5)

        # Create a mock request (not used by the generator directly)
        request = _make_mock_request()
        response = await stream.sse_endpoint(request)

        # Push an event and read output
        event = VaultEvent(event_type="created", path="inbox/test.md")
        await watcher.push_event(event)

        gen = response.body_iterator
        chunk = await gen.__anext__()
        lines = chunk.strip().split("\n")

        assert lines[0] == "event: created"
        assert lines[1].startswith("data: ")
        data = json.loads(lines[1][len("data: ") :])
        assert data["event_type"] == "created"
        assert data["path"] == "inbox/test.md"

        # Clean up
        await gen.aclose()

    async def test_heartbeat(self):
        """With short heartbeat timeout, heartbeat comment should be emitted."""
        watcher = MockWatcher()
        stream = VaultEventStream(watcher, heartbeat_seconds=1)

        request = _make_mock_request()
        response = await stream.sse_endpoint(request)

        gen = response.body_iterator
        # No events pushed, so after timeout we get heartbeat
        chunk = await asyncio.wait_for(gen.__anext__(), timeout=3.0)
        assert chunk.strip() == ": heartbeat"

        await gen.aclose()

    async def test_multiple_events(self):
        """Multiple events should stream sequentially."""
        watcher = MockWatcher()
        stream = VaultEventStream(watcher, heartbeat_seconds=30)

        request = _make_mock_request()
        response = await stream.sse_endpoint(request)
        gen = response.body_iterator

        events = [
            VaultEvent(event_type="created", path="inbox/a.md"),
            VaultEvent(event_type="modified", path="inbox/b.md"),
            VaultEvent(event_type="deleted", path="inbox/c.md"),
        ]

        for ev in events:
            await watcher.push_event(ev)

        collected = []
        for _ in range(3):
            chunk = await asyncio.wait_for(gen.__anext__(), timeout=3.0)
            collected.append(chunk)

        assert "event: created" in collected[0]
        assert "event: modified" in collected[1]
        assert "event: deleted" in collected[2]

        await gen.aclose()

    async def test_unsubscribe_on_close(self):
        """Closing the generator should unsubscribe from the watcher."""
        watcher = MockWatcher()
        stream = VaultEventStream(watcher, heartbeat_seconds=30)

        request = _make_mock_request()
        response = await stream.sse_endpoint(request)
        gen = response.body_iterator

        assert watcher.subscriber_count == 1

        # Push one event so generator advances past the first await
        await watcher.push_event(VaultEvent(event_type="created", path="test.md"))
        await asyncio.wait_for(gen.__anext__(), timeout=3.0)

        # Close the generator
        await gen.aclose()

        assert watcher.subscriber_count == 0

    async def test_response_headers(self):
        """SSE response should have correct streaming headers."""
        watcher = MockWatcher()
        stream = VaultEventStream(watcher, heartbeat_seconds=15)

        request = _make_mock_request()
        response = await stream.sse_endpoint(request)

        assert response.media_type == "text/event-stream"
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.headers["Connection"] == "keep-alive"
        assert response.headers["X-Accel-Buffering"] == "no"

        # Clean up the body iterator
        await response.body_iterator.aclose()

    async def test_moved_event_includes_old_path(self):
        """Moved events should include old_path in the SSE data."""
        watcher = MockWatcher()
        stream = VaultEventStream(watcher, heartbeat_seconds=30)

        request = _make_mock_request()
        response = await stream.sse_endpoint(request)
        gen = response.body_iterator

        event = VaultEvent(
            event_type="moved",
            path="decisions/renamed.md",
            old_path="inbox/original.md",
        )
        await watcher.push_event(event)

        chunk = await asyncio.wait_for(gen.__anext__(), timeout=3.0)
        lines = chunk.strip().split("\n")
        assert lines[0] == "event: moved"
        data = json.loads(lines[1][len("data: ") :])
        assert data["old_path"] == "inbox/original.md"
        assert data["path"] == "decisions/renamed.md"

        await gen.aclose()


class _MockRequest:
    """Minimal mock of starlette.requests.Request."""

    pass


def _make_mock_request():
    return _MockRequest()
