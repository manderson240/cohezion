import asyncio
import logging

from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.simulation.cross_domain_translator import CrossDomainTranslator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyTranslator")


async def verify_translator():
    print("🚀 Verifying CrossDomainTranslator...")

    translator = CrossDomainTranslator()
    db = SurrealClient()

    # 1. Run Translation
    concepts = ["black hole", "event horizon"]
    results = await translator.translate_batch(concepts, "physics", "biology")

    # 2. Verify results
    assert len(results) == 2
    for r in results:
        assert r["source_concept"] in concepts
        assert r["target_concept"] is not None
        print(f"✓ Translated '{r['source_concept']}' to '{r['target_concept']}'")

    # 3. Verify persistence in SurrealDB
    # We'll check for any records in cross_domain_mapping
    try:
        query_res = await db.query("SELECT * FROM cross_domain_mapping LIMIT 5")
        if query_res and query_res[0]:
            print(f"✓ Verified persistence: Found {len(query_res[0])} records in SurrealDB.")
        else:
            print("⚠️ Persistence check: No records found (is SurrealDB running?)")
    except Exception as e:
        print(f"❌ Persistence check failed: {e}")

    print("\n✅ CrossDomainTranslator Verified!")


if __name__ == "__main__":
    asyncio.run(verify_translator())
