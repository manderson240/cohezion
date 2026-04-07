"""
Moshi Full-Duplex Client.
Provides WebSocket handlers for Kyutai's Moshi foundation model.
Enables ~200ms latency, interruptible voice interaction.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import websockets


logger = logging.getLogger(__name__)


class MoshiClient:
    """
    Client for Moshi foundation model server.
    Handles streaming audio in/out over WebSockets.
    """

    def __init__(self, server_url: str = "ws://localhost:8998/ws"):
        self.server_url = server_url
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._running = False

    async def connect(self):
        """Establish WebSocket connection to Moshi server."""
        try:
            self._ws = await websockets.connect(self.server_url)
            self._running = True
            logger.info("Connected to Moshi server at %s", self.server_url)
        except Exception as e:
            logger.error("Failed to connect to Moshi server: %s", e)
            raise

    async def disconnect(self):
        """Close WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
            logger.info("Disconnected from Moshi server")

    async def converse(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[bytes | str]:
        """
        Full-duplex conversation loop.
        Sends audio chunks and yields response audio or text.
        """
        if not self._ws:
            await self.connect()

        # Task to handle incoming messages
        async def _receiver():
            try:
                async for message in self._ws:
                    if isinstance(message, bytes):
                        # Response audio chunk
                        yield message
                    else:
                        # Response text or metadata
                        data = json.loads(message)
                        if "text" in data:
                            yield data["text"]
            except Exception as e:
                logger.error("Moshi receiver error: %s", e)

        # Send audio task
        async def _sender():
            try:
                async for chunk in audio_stream:
                    if not self._running:
                        break
                    await self._ws.send(chunk)
            except Exception as e:
                logger.error("Moshi sender error: %s", e)

        # Run both tasks
        # Note: This is a simplified version. A real implementation would
        # manage the concurrency more robustly.
        
        # For this prototype, we yield from receiver while sender runs in background
        sender_task = asyncio.create_task(_sender())
        
        try:
            async for item in _receiver():
                yield item
        finally:
            sender_task.cancel()
            await self.disconnect()

    async def speak_and_listen(self, text: str) -> str:
        """
        Simple text-to-speech-to-text interaction.
        Useful for agents communicating with the operator.
        """
        if not self._ws:
            await self.connect()

        # Send text as a prompt (if supported by server implementation)
        await self._ws.send(json.dumps({"text": text}))
        
        # Wait for text response
        async for message in self._ws:
            if not isinstance(message, bytes):
                data = json.loads(message)
                if "text" in data:
                    return data["text"]
        
        return ""
