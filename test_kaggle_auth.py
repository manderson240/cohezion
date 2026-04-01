import os

from dotenv import load_dotenv


def test_auth():
    load_dotenv()
    
    username = os.getenv("KAGGLE_USERNAME")
    key = os.getenv("KAGGLE_API_TOKEN")
    
    if key and key.startswith("KGAT_"):
        key = key[5:]
        
    print(f"Testing auth for user: {username}")
    
    # Set environment variables BEFORE importing KaggleApi if possible, 
    # but certainly before instantiating.
    os.environ["KAGGLE_USERNAME"] = username
    os.environ["KAGGLE_KEY"] = key
    
    from kaggle.api.kaggle_api_extended import KaggleApi
    
    api = KaggleApi()
    try:
        api.authenticate()
        print("Authentication successful!")
        comps = api.competitions_list(search="nemotron")
        print(f"Successfully listed {len(comps)} competitions.")
    except Exception as e:
        print(f"Authentication failed: {e}")

if __name__ == "__main__":
    test_auth()
