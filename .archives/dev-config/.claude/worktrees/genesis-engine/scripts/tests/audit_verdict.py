import asyncio
import logging

from cohezion.core.persistence.surreal_client import SurrealClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AuditVerdict")


async def audit():
    db = SurrealClient()

    query = "SELECT id, metadata.topic, metadata.grade, metadata.feedback FROM universe_nodes WHERE node_type = 'research_paper'"
    res = await db.query(query)

    if isinstance(res, list) and res:
        items = res[0].get("result", [])
        logger.info(f"Found {len(items)} papers.")
        for item in items:
            meta = item.get("metadata", {})
            logger.info(f"Paper: {meta.get('topic')}")
            logger.info(f"   Grade: {meta.get('grade')}")
            logger.info(f"   Feedback: {meta.get('feedback')}")
            logger.info("-" * 20)


if __name__ == "__main__":
    asyncio.run(audit())
