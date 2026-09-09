import urllib.request
import json
import subprocess

def get_page(page_name):
    # Kaggle API page fetch if available
    res = subprocess.run(["kaggle", "competitions", "data", "-c", "pokemon-tcg-ai-battle-challenge-strategy"], capture_output=True, text=True)
    print(res.stdout[:500])

get_page("rules")
