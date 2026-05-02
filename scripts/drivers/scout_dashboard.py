from pathlib import Path

import requests


# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3-coder:30b"
TARGET_FILE = "src/cohezion/ui/fractal_dashboard.py"


def scout_dashboard():
    print(f"Scouting {TARGET_FILE} with {MODEL}...")
    code = Path(TARGET_FILE).read_text()

    prompt = f"""
    Internal Monologue: Critique this Streamlit dashboard code:
    {code}

    Suggest 3 improvements for:
    1. Performance (Caching?)
    2. Aesthetics (CSS tweaks?)
    3. Functionality (Interactiveness?)
    """

    try:
        response = requests.post(
            OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False}
        )
        print("\n=== SCOUT REPORT ===\n")
        print(response.json()["response"])
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    scout_dashboard()
