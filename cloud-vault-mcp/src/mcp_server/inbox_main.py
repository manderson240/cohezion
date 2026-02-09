"""Entry point for the inbox processor daemon."""

import asyncio
import json
import logging
import signal
from pathlib import Path

from .compound_ops import CompoundOps
from .config import ServerConfig
from .inbox_processor import InboxProcessor
from .obsidian_ops import ObsidianOps
from .vault_ops import VaultOps
from .vault_watcher import VaultFileWatcher


logger = logging.getLogger("inbox-processor")


def _load_oauth_token() -> str | None:
    """Read access token from Claude Code's credentials file."""
    creds_path = Path.home() / ".claude" / ".credentials.json"
    try:
        data = json.loads(creds_path.read_text())
        return data["claudeAiOauth"]["accessToken"]
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return None


async def run_inbox_daemon(config: ServerConfig):
    """Run the inbox processor daemon."""
    vault = VaultOps(config.vault_path)
    obsidian = ObsidianOps(vault)
    compound = CompoundOps(vault, obsidian)

    # Import anthropic here to make it optional
    try:
        import anthropic
    except ImportError:
        logger.error(
            "anthropic package required. Install with: pip install anthropic>=0.40.0"
        )
        return

    # Try OAuth token first, fall back to API key
    auth_token = _load_oauth_token()
    if auth_token:
        client = anthropic.Anthropic(auth_token=auth_token)
        logger.info("Using OAuth token from ~/.claude/.credentials.json")
    elif config.anthropic_api_key:
        client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        logger.info("Using ANTHROPIC_API_KEY")
    else:
        logger.error("No auth: set ANTHROPIC_API_KEY or log in with Claude Code")
        return
    processor = InboxProcessor(vault, compound, client, model=config.inbox_model)

    loop = asyncio.get_running_loop()
    watcher = VaultFileWatcher(
        config.vault_path, loop, debounce_seconds=config.inbox_debounce_seconds
    )
    queue = watcher.subscribe()
    watcher.start()

    logger.info("Inbox processor daemon started, watching %s/inbox/", config.vault_path)

    shutdown = asyncio.Event()

    def handle_signal():
        logger.info("Shutdown signal received")
        shutdown.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    try:
        while not shutdown.is_set():
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
            except TimeoutError:
                continue

            if event.event_type in (
                "created",
                "modified",
            ) and processor.should_process(event.path):
                logger.info("Processing inbox note: %s", event.path)
                try:
                    result = await processor.process_note(event.path)
                    if result.success:
                        logger.info("Filed: %s -> %s", result.source, result.target)
                    else:
                        logger.warning("Failed: %s -- %s", result.source, result.error)
                except Exception:
                    logger.exception("Unexpected error processing %s", event.path)
    finally:
        watcher.stop()
        logger.info("Inbox processor daemon stopped")


def main():
    """Entry point for the inbox-processor command."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = ServerConfig.from_env()
    asyncio.run(run_inbox_daemon(config))


if __name__ == "__main__":
    main()
