import asyncio
import logging
import os
import sys


sys.path.append(os.path.abspath("src"))
from cohezion.core.persistence.admin import DBAdmin


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PulseVerify")


async def verify_pulse():
    dba = DBAdmin()
    await dba.connect()

    # Query recent pulse
    query = "SELECT * FROM system_pulse ORDER BY timestamp DESC LIMIT 3;"
    try:
        response = await dba.client.query(query)
        # Parse (depending on client wrapper)
        if hasattr(response, "result"):
            # If direct AsyncSurreal object, it might differ.
            # DBAdmin wraps client.
            # Let's inspect raw response
            pass

        rows = []
        if isinstance(response, list) and len(response) > 0:
            rows = response[0].get("result", response)

        if not rows:
            logger.error("❌ No system_pulse records found!")
            return

        latest = rows[0]
        logger.info(f"✅ Found {len(rows)} pulse records.")
        logger.info(f"Latest Timestamp: {latest.get('timestamp')}")
        logger.info(f"Hardware Vitals: {latest.get('hardware', {}).keys()}")
        logger.info(f"Software Vitals: {latest.get('software', {}).keys()}")

        # Validation
        if "cpu_percent" in latest.get("hardware", {}) and "total_pending" in latest.get("software", {}):
            logger.info("✅ Data Integrity Verified: Hardware and Software fusion successful.")
        else:
            logger.error("❌ Data Integrity Failed: Missing keys.")

    except Exception as e:
        logger.error(f"Verification Query Failed: {e}")
    finally:
        await dba.close()


if __name__ == "__main__":
    asyncio.run(verify_pulse())
