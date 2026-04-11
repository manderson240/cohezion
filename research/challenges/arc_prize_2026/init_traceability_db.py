import asyncio
import httpx


async def init_db():
    url = "http://localhost:8001/sql"
    auth = ("root", "root")

    # 1. Define NS and DB
    print("Defining Namespace and Database...")
    body = "DEFINE NAMESPACE cohezion; DEFINE DATABASE traceability ON NAMESPACE cohezion;"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, content=body, auth=auth)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.text}")

    # 2. Run the actual schema file
    print("\nInitializing Schema...")
    from pathlib import Path

    schema_path = Path("src/cohezion/knowledge_graph/plan_traceability_schema.surql")
    schema_text = schema_path.read_text()

    # We need to strip the 'USE' statement if it's causing issues, or just rely on headers
    headers = {"NS": "cohezion", "DB": "traceability"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, content=schema_text, headers=headers, auth=auth)
        print(f"  Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"  Error: {resp.text}")
        else:
            print("  Schema initialized successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
