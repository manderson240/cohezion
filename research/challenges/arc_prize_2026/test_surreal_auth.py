import asyncio
import httpx

async def test_auth(port):
    url = f"http://localhost:{port}/sql"
    headers = {
        "Accept": "application/json",
        "NS": "cohezion",
        "DB": "traceability",
    }
    auth = ("root", "root")
    body = "USE NS cohezion DB traceability; INFO FOR DB;"
    
    print(f"Testing port {port}...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, content=body, headers=headers, auth=auth)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"  Success! Response: {resp.json()}")
            else:
                print(f"  Failed: {resp.text}")
    except Exception as e:
        print(f"  Error: {e}")

async def main():
    await test_auth(8000)
    await test_auth(8001)

if __name__ == "__main__":
    asyncio.run(main())
