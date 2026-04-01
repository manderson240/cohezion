import asyncio
import os

from cohezion.integrations.kaggle_api import KaggleAPI


async def list_competitions():
    username = "manderson240"
    key = os.environ.get("KAGGLE_API_TOKEN")
    
    if not key:
        print("Error: KAGGLE_API_TOKEN not found in environment.")
        return

    api = KaggleAPI(username=username, key=key)
    
    try:
        response = await api._handle_request("GET", "/competitions/list?search=nemotron")
        data = response.json()
        print(f"Competitions found: {data}")
    except Exception as e:
        print(f"Failed to list competitions: {e}")

if __name__ == "__main__":
    asyncio.run(list_competitions())
