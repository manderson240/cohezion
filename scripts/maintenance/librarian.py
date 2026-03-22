import asyncio
import logging
from datetime import datetime, timedelta

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO, format="%(asctime)s - [LIBRARIAN] - %(message)s")
logger = logging.getLogger("Librarian")


class Librarian:
    """
    The Librarian: Curates the Knowledge Graph.
    - Prunes low-quality nodes.
    - Archives medium-quality nodes.
    - Merges duplicates.
    """

    def __init__(self):
        self.db = SurrealClient()

    async def run_curation_cycle(self):
        logger.info("📚 Librarian Curating Stacks...")

        await self.prune_junk()
        await self.deduplicate()

        logger.info("✅ Curation Cycle Complete.")

    async def prune_junk(self):
        """Delete Grade < 0.5 older than 7 days."""
        try:
            # SurrealQL time math is tricky, doing it in python for safety
            # Fetch candidates
            query = "SELECT id, created_at, metadata.grade FROM universe_nodes WHERE node_type = 'research_paper' AND metadata.grade < 0.5"
            response = await self.db.query(query)

            candidates = []
            if isinstance(response, list) and response and isinstance(response[0], dict):
                candidates = response[0].get("result", [])

            deleted_count = 0
            cutoff = datetime.now() - timedelta(days=7)

            for item in candidates:
                created_at_str = item.get("created_at")
                if not created_at_str:
                    continue

                # Rough ISO parsing
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    # Timezone naive comparison fix
                    if created_at.tzinfo:
                        created_at = created_at.replace(tzinfo=None)

                    if created_at < cutoff:
                        logger.info(f"🗑️ Pruning Junk: {item['id']} (Grade {item['metadata'].get('grade')})")
                        await self.db.delete_node(item["id"])
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"Date parse error {item['id']}: {e}")

            if deleted_count > 0:
                logger.info(f"🧹 Pruned {deleted_count} junk nodes.")

        except Exception as e:
            logger.error(f"Pruning failed: {e}")

    async def deduplicate(self):
        """Find nodes with same Topic and keep the best one."""
        try:
            # 1. Get all topics (This is heavy, optimizable later)
            query = "SELECT id, metadata.topic, metadata.grade FROM universe_nodes WHERE node_type = 'research_paper'"
            response = await self.db.query(query)

            items = []
            if isinstance(response, list) and response and isinstance(response[0], dict):
                items = response[0].get("result", [])

            # Group by Topic
            topics = {}
            for item in items:
                t = item["metadata"].get("topic")
                if not t:
                    continue
                if t not in topics:
                    topics[t] = []
                topics[t].append(item)

            merged_count = 0

            for t, nodes in topics.items():
                if len(nodes) > 1:
                    # Sort by Grade DESC
                    nodes.sort(key=lambda x: x["metadata"].get("grade", 0.0), reverse=True)

                    winner = nodes[0]
                    losers = nodes[1:]

                    logger.info(
                        f"dup Detected for '{t}'. Keeping {winner['id']} (Grade {winner['metadata'].get('grade')})"
                    )

                    for loser in losers:
                        # In a real system, we'd move edges from loser to winner.
                        # For now, just delete.
                        logger.info(f"   Deleting duplicate: {loser['id']}")
                        await self.db.delete_node(loser["id"])
                        merged_count += 1

            if merged_count > 0:
                logger.info(f"🔗 Merged/Deleted {merged_count} duplicate nodes.")

        except Exception as e:
            logger.error(f"Deduplication failed: {e}")


if __name__ == "__main__":

    async def main():
        lib = Librarian()
        await lib.run_curation_cycle()

    asyncio.run(main())
