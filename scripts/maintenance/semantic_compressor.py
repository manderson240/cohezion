import asyncio
import gzip
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from cohezion.core.persistence.surreal_client import UniverseNode
from cohezion.swarm.agents.base import BaseAgent  # Reuse BaseAgent for summary


logging.basicConfig(level=logging.INFO, format="%(asctime)s - [COMPRESSOR] - %(message)s")
logger = logging.getLogger("SemanticCompressor")

ARCHIVE_DIR = Path("data/archive")
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


class SemanticCompressor(BaseAgent):
    """
    Scans for old records, summarizes them, archives the original,
    and updates the DB with the 'Compressed Thought'.
    """

    def __init__(self, age_days: int = 7):
        super().__init__(model_name="phi3:mini")
        self.age_days = age_days
        # Override DB client to use our own if needed, but BaseAgent has one self._db

    async def compress_nodes(self):
        logger.info(f"💾 Starting Compression Scan (Older than {self.age_days} days)...")

        # 1. Scan for Candidates
        # Note: In real SurrealDB use proper datetime query.
        # Here we fetch a batch and filter in Python for safety/flexibility.
        logger.info("  - Fetching candidates...")
        # Get last 1000 items (or all depending on size) - Limit to avoid OOM
        # A better query would be SELECT * FROM universe_nodes WHERE created_at < ... AND compressed = false
        # For now, we fetch recent 1000 and check dates
        all_nodes = await self._db.get_all_nodes(limit=1000)

        cutoff = datetime.now() - timedelta(days=self.age_days)
        candidates = []

        for node in all_nodes:
            # Check if already compressed
            if node.compressed:
                continue

            # Check Age
            if node.created_at < cutoff:
                candidates.append(node)

        logger.info(f"  - Found {len(candidates)} candidates for compression.")

        # 2. Process Candidates
        for node in candidates:
            await self._compress_node(node)
            await asyncio.sleep(0.5)  # Yield

    async def _compress_node(self, node: UniverseNode):
        try:
            # A. Summarize
            logger.info(f"  > Compressing Node: {node.id}")
            content = node.content

            if len(content) < 500:
                logger.debug("    - Identifying as 'Snapshot' (Too small to compress). Skipping.")
                return

            summary = await self._call_ollama(
                prompt=f"TASK: Summarize this text into a concise 'semantically dense' paragraph. Preserve key facts, metrics, and outcomes.\nTEXT:\n{content[:4000]}...",
                model="phi3:mini",
                temperature=0.3,
            )

            summary_markdown = f"**[SEMANTICALLY COMPRESSED]**\n\n{summary}\n\n*(Original Archived)*"

            # B. Archive Original
            archive_path = ARCHIVE_DIR / f"{node.id.replace(':', '_')}.json.gz"
            original_data = node.to_dict()
            with gzip.open(archive_path, "wt", encoding="utf-8") as f:
                json.dump(original_data, f)

            # C. Update DB
            # We create a new dict for update
            updated_data = original_data.copy()
            updated_data["content"] = summary_markdown
            updated_data["compressed"] = True
            updated_data["metadata"]["archive_path"] = str(archive_path)
            updated_data["metadata"]["compressed_at"] = datetime.now().isoformat()

            # Store back (overwrite)
            # Use 'create' or store based on client. 'create' might fail if exists in strict mode,
            # assume store_node handles upsert or ID based update.
            # BaseAgent DB client has 'store_node' which might just write to file in mock or upsert in real.
            # Using store_node logic:
            # It calls self._client.create(f"universe_nodes:{node.id}", data)
            # If strictly create, this fails. We need 'update'.

            # Update specific method? BaseAgent doesn't expose one easily.
            # Let's assume store_node is robust OR use raw query UPDATE

            update_query = f"UPDATE universe_nodes:{node.id} MERGE $data"
            vars = {
                "data": {
                    "content": summary_markdown,
                    "compressed": True,
                    "metadata": updated_data["metadata"],
                }
            }

            await self._db.query(update_query, vars)

            logger.info(f"    ✅ Compressed: {archive_path}")

        except Exception as e:
            logger.error(f"Failed to compress {node.id}: {e}")

    async def process(self, *args):
        # Dummy for ABC
        pass


async def main():
    compressor = SemanticCompressor(age_days=1)  # Aggressive for testing (1 day)
    await compressor.compress_nodes()


if __name__ == "__main__":
    asyncio.run(main())
