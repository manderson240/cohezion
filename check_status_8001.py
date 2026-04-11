import asyncio
import os
import sys

# Add src to PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from cohezion.core.persistence.surreal_client import SurrealClient
except ImportError as e:
    print(f"Error importing cohezion: {e}")
    sys.exit(1)


async def check():
    # Connect to port 8001
    db = SurrealClient(url="ws://localhost:8001/rpc")
    print("Connecting to SurrealDB at ws://localhost:8001/rpc...")
    connected = await db.connect()
    if not connected:
        print("Failed to connect to SurrealDB")
        return

    try:
        # Check specifically for the BBQ checkpoints (Nemotron track)
        print("Checking Nemotron (BBQ) status...")
        query = 'SELECT * FROM agent_journeys WHERE journey_id CONTAINS "sim_bbq" OR metadata.track CONTAINS "nemotron" ORDER BY started_at DESC LIMIT 5'
        res = await db.query(query)
        print(f"NEMOTRON STATUS: {res}")

        # Check for Cognitive AGI track
        print("\nChecking Cognitive AGI status...")
        query = 'SELECT * FROM agent_journeys WHERE journey_id CONTAINS "agi" OR metadata.track CONTAINS "agi" ORDER BY started_at DESC LIMIT 5'
        res = await db.query(query)
        print(f"AGI STATUS: {res}")

        # Check for any active background tasks
        print("\nChecking active background tasks...")
        query = 'SELECT * FROM agent_journeys WHERE status = "IN_PROGRESS" LIMIT 10'
        res = await db.query(query)
        print(f"ACTIVE TASKS: {res}")

    except Exception as e:
        print(f"Error during query: {e}")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(check())
