import httpx
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

class FindingsDispatcher:
    """
    Dispatches findings to external webhooks (Discord, Slack, etc.)
    """
    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.getenv("FINDINGS_WEBHOOK_URL")

    async def dispatch(self, title: str, message: str, color: int = 0x4ECDC4):
        """Send a formatted embed to the webhook."""
        if not self.webhook_url:
            logger.warning("No FINDINGS_WEBHOOK_URL set. Skipping external dispatch.")
            return

        payload = {
            "embeds": [{
                "title": f"🚀 Cohezion Finding: {title}",
                "description": message,
                "color": color,
                "timestamp": None # Discord auto-stamps
            }]
        }

        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(self.webhook_url, json=payload)
                res.raise_for_status()
                logger.info(f"Finding dispatched to external webhook: {title}")
            except Exception as e:
                logger.error(f"Failed to dispatch finding: {e}")

async def main():
    # Test dispatch
    dispatcher = FindingsDispatcher()
    await dispatcher.dispatch(
        "Epoch Transition",
        "Universe has reached the **Omega Point**. Stability 1.0 reached."
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
