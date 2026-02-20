import asyncio
import logging

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugQuery")


async def debug_query():
    db = SurrealClient()

    queries = [
        "SELECT count() FROM universe_nodes WHERE node_type = 'research_paper'",
        "SELECT count() FROM universe_nodes WHERE node_type = 'research_paper' AND metadata.feedback IS NONE",
        "SELECT count() FROM universe_nodes WHERE node_type = 'research_paper' AND metadata.feedback = NULL",
        "SELECT * FROM universe_nodes WHERE node_type = 'research_paper' AND (metadata.feedback IS NONE OR metadata.feedback = NULL) LIMIT 10",  # The failing query
    ]

    for q in queries:
        logger.info(f"RUNNING: {q}")
        res = await db.query(q)
        logger.info(f"RESULT: {res}")


if __name__ == "__main__":
    asyncio.run(debug_query())
