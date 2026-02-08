"""Entry point for the inbox processor daemon."""

import asyncio
import logging
import signal

from .compound_ops import CompoundOps
from .config import ServerConfig
from .inbox_processor import InboxProcessor
from .obsidian_ops import ObsidianOps
from .vault_ops import VaultOps
from .vault_watcher import VaultFileWatcher


logger = logging.getLogger("inbox-processor")


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

    if not config.anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY environment variable required")
        return

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
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
