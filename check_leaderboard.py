import asyncio
import os

from cohezion.integrations.kaggle_api import KaggleAPI


async def check_leaderboard():
    username = "manderson240"
    # Note: Token is retrieved from environment or .env
    # For this check, I'll assume it's passed or available.
    # In a real run, I'd read it directly.
    key = os.environ.get("KAGGLE_API_TOKEN")
    
    if not key:
        print("Error: KAGGLE_API_TOKEN not found in environment.")
        return

    api = KaggleAPI(username=username, key=key)
    competition_id = "nvidia-nemotron-model-reasoning-challenge"
    
    # Kaggle API for leaderboard: GET /competitions/leaderboard/view/{id}
    path = f"/competitions/leaderboard/view/{competition_id}"
    
    try:
        response = await api._handle_request("GET", path)
        data = response.json()
        
        # Search for our user in the leaderboard
        found = False
        for entry in data.get("submissions", []):
            if entry.get("teamName") == username or entry.get("teamId") == username:
                print(f"User {username} found on leaderboard!")
                print(f"Rank: {entry.get('rank')}")
                print(f"Score: {entry.get('score')}")
                found = True
                break
        
        if not found:
            # Check for general status or empty list
            print(f"User {username} not found in the first page of the leaderboard for {competition_id}.")
            
    except Exception as e:
        print(f"Failed to fetch leaderboard: {e}")

if __name__ == "__main__":
    asyncio.run(check_leaderboard())
