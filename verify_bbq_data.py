import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from cohezion.db.surreal_client import SurrealClient

async def main():
    db = SurrealClient()
    await db.connect()
    
    print("\n--- LAST 5 RECORDS ---")
    # Fetch last 5 records
    res = await db.query('SELECT * FROM agent_journeys ORDER BY started_at DESC LIMIT 5')
    
    # SurrealDB Client .query() typically returns a list of results for each query statement
    # Each result is a dict with 'status', 'time', 'result' keys OR just the data depending on the client version/wrapping.
    # Let's inspect 'res' more robustly.
    
    records = []
    if isinstance(res, list) and len(res) > 0:
        if 'result' in res[0]:
             records = res[0]['result']
        else:
             records = res # Maybe it's just the list of records?
    elif isinstance(res, dict) and 'result' in res:
        records = res['result']

    if records:
        for rec in records:
            print(f"ID: {rec.get('journey_id', 'N/A')}")
            print(f"Response: {rec.get('final_response', 'N/A')}")
            # Check for STEPS/NARRATION
            steps = rec.get('steps', [])
            if steps:
                print(f"Narrative: {steps[0].get('narration', 'No narration')}")
            else:
                print("Narrative: NONE")
            print(f"Substrate: {rec.get('metadata', {}).get('substrate', 'N/A')}")
            print("-" * 40)
    else:
        print(f"No records found or unexpected format: {res}")
        
    await db.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
