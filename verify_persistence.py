import asyncio
import logging
from pathlib import Path
from cohezion.simulation.enhanced_simulator import EnhancedSimulator
from cohezion.core.persistence.surreal_client import SurrealClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyPersistence")

async def verify():
    logger.info("🚀 Starting Persistence Verification...")
    
    # Initialize simulator
    simulator = EnhancedSimulator(output_dir=Path("tests/temp_sim"))
    
    # Run a single simulation
    logger.info("🏃 Running single simulation...")
    result = await simulator.run_simulation("architect")
    logger.info(f"✅ Simulation complete: {result.sim_id}")
    
    # Check SurrealDB directly
    db = SurrealClient()
    await db.connect()
    
    logger.info("🔍 Listing all IDs in agent_journeys...")
    all_res = await db.query("SELECT id, journey_id FROM agent_journeys")
    print(f"All Records: {all_res}")
    
    # Check for our specific ID
    found = False
    if all_res and all_res[0].get("result"):
        for record in all_res[0]["result"]:
            rid = str(record["id"])
            jid = record.get("journey_id")
            if result.sim_id in rid or result.sim_id == jid:
                logger.info(f"🎉 FOUND IT: {rid}")
                found = True
                break
    
    if found:
        logger.info("🎉 SUCCESS: Journey found in SurrealDB!")
        print("JOURNEY_PERSISTENCE_VERIFIED")
    else:
        logger.error("❌ FAILURE: Journey not found in SurrealDB.")
        print("JOURNEY_PERSISTENCE_FAILED")
        
    await db.close()

if __name__ == "__main__":
    asyncio.run(verify())
