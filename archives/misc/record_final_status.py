import asyncio
import json
import os
import sys
from datetime import datetime


# Add src to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "src"))

from cohezion.core.persistence.surreal_client import SurrealClient


async def record():
    # Use port 8001
    db = SurrealClient(url="ws://localhost:8001/rpc", namespace="cohezion", database="universe")
    print("Connecting to SurrealDB...")
    await db.connect()

    try:
        journey_id = f"journey_reboot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        data = {
            "journey_id": journey_id,
            "status": "ACTIVE",
            "started_at": datetime.now().isoformat(),
            "metadata": {
                "track_2_nemotron": "v26_running_on_kaggle_blackwell",
                "track_3_agi": "manual_tasks_verified",
                "track_4_birdclef": "cpu_baseline_verified",
                "session_breakthroughs": [
                    "PTXAS fix",
                    "Teacher distillation integrated",
                    "AST model pre-loading",
                ],
            },
            "summary": "Pre-reboot state preservation. Nemotron v26 is running. AGI and BirdCLEF baselines stabilized.",
        }

        # Insert record into agent_journeys
        # Since I previously saw the table doesn't exist in some DBs, I'll ensure it's created
        res = await db.query(f"CREATE agent_journeys CONTENT {json.dumps(data)};")
        print(f"Recorded status in SurrealDB: {res}")

    except Exception as e:
        print(f"Error recording status: {e}")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(record())
