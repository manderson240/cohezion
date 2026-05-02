"""Server-Sent Events stream for vault change notifications."""

import asyncio
import json
import logging

from starlette.requests import Request
from starlette.responses import StreamingResponse

from .vault_watcher import VaultFileWatcher


logger = logging.getLogger(__name__)


class VaultEventStream:
    """SSE endpoint that streams vault events to HTTP clients."""

    def __init__(self, watcher: VaultFileWatcher, heartbeat_seconds: int = 15):
        self._watcher = watcher
        self._heartbeat_seconds = heartbeat_seconds

    async def sse_endpoint(self, request: Request) -> StreamingResponse:
        """SSE endpoint handler for GET /events/vault."""
        queue = self._watcher.subscribe()

        async def event_generator():
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(
                            queue.get(), timeout=float(self._heartbeat_seconds)
                        )
                        data = json.dumps(event.to_dict())
                        yield f"event: {event.event_type}\ndata: {data}\n\n"
                    except TimeoutError:
                        yield ": heartbeat\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                self._watcher.unsubscribe(queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
