import asyncio
import httpx

async def complete_tasks():
    url = "http://localhost:8001/sql"
    auth = ("root", "root")
    headers = {"NS": "cohezion", "DB": "traceability"}
    
    # We want to update task:arc_deep_synthesis_plan__1_4
    body = """
    UPDATE task:arc_deep_synthesis_plan__1_4 SET status = 'completed', completed_at = time::now();
    UPDATE plan:arc_deep_synthesis_plan SET tasks_completed += 1;
    """
    
    print("Marking task 1.4 as completed in SurrealDB...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, content=body, headers=headers, auth=auth)
        if resp.status_code == 200:
            print("Successfully updated tasks.")
        else:
            print(f"Error: {resp.text}")

if __name__ == "__main__":
    asyncio.run(complete_tasks())
