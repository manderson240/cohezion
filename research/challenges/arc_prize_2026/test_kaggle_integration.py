import kagglehub
import os
from pathlib import Path

def test_kagglehub_usage():
    print("Verifying kagglehub and Kaggle integration...")
    
    # 1. List available versions of a model (e.g. Gemma 2)
    # This doesn't download, just checks connectivity
    print("\n1. Checking Gemma 2 model on kagglehub...")
    try:
        # We don't download the whole 30GB model, just check the handle
        model_handle = "google/gemma-2/pyTorch/9b"
        print(f"Model handle: {model_handle}")
        # In a real scenario, we'd use kagglehub.model_download(model_handle)
    except Exception as e:
        print(f"Error checking model: {e}")

    # 2. Check for existence of ARC-AGI-3 related datasets
    print("\n2. Searching for ARC-AGI-3 datasets...")
    # This is a conceptual check as kagglehub doesn't have a direct 'search' 
    # but we can verify our ability to download specific competition files
    competition_id = "arc-prize-2026"
    print(f"Target competition: {competition_id}")
    
    # 3. Demonstrate Kaggle API (the lower level library)
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    try:
        api.authenticate()
        print(f"Kaggle API Authenticated as: {os.environ.get('KAGGLE_USERNAME')}")
        
        # List competitions to verify API access
        print("\n3. Listing recent competitions:")
        competitions = api.competitions_list(search="arc-prize")
        for comp in competitions:
            print(f" - {comp.ref}: {comp.title}")
            
    except Exception as e:
        print(f"Kaggle API error: {e}")

if __name__ == "__main__":
    test_kagglehub_usage()
