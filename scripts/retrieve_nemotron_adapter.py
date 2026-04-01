#!/usr/bin/env python3
"""
Retrieve trained LoRA adapter from completed Kaggle notebook.
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()

# Set Kaggle credentials for all libraries
username = os.getenv("KAGGLE_USERNAME") or os.getenv("username")
api_token = os.getenv("KAGGLE_API_TOKEN")

if api_token and api_token.startswith("KGAT_"):
    api_token = api_token[5:]

if username:
    os.environ["KAGGLE_USERNAME"] = username
if api_token:
    os.environ["KAGGLE_KEY"] = api_token

from cohezion.integrations.kaggle_api import KaggleAPI


async def retrieve_trained_adapter(notebook_name: str):
    """Retrieve the trained LoRA adapter from a completed Kaggle notebook."""
    if not username or not api_token:
        print("❌ Missing KAGGLE_USERNAME or KAGGLE_API_TOKEN in .env")
        return False

    print(f"🔍 Retrieving adapter from notebook: {notebook_name}")

    api = KaggleAPI(username=username, key=api_token)

    try:
        # First check if notebook is complete
        status = await api.get_notebook_status(notebook_name)
        print(f"📊 Notebook status: {status}")

        if status != "complete":
            print(f"⏳ Notebook is not complete yet (status: {status}). Cannot retrieve adapter.")
            return False

        # Create directory for retrieved files
        retrieve_dir = Path(f"data/retrieved_{notebook_name}")
        retrieve_dir.mkdir(parents=True, exist_ok=True)

        print(f"📥 Retrieving notebook output to: {retrieve_dir}")

        # Retrieve the notebook output/files
        # Note: This retrieves output files, not the model itself
        # For actual model retrieval, we'd need to save it during training and then get it
        result = await api.kernels_output(notebook_name, path=str(retrieve_dir))

        print(f"✅ Notebook output retrieved successfully!")
        print(f"📁 Files saved to: {retrieve_dir.absolute()}")

        # List what we retrieved
        files = list(retrieve_dir.iterdir())
        if files:
            print(f"📄 Retrieved files:")
            for file in files:
                print(f"  - {file.name}")
        else:
            print(f"📄 No files retrieved (this is expected for model outputs)")
            print(f"💡 To get the actual model, you need to:")
            print(f"   1. Go to the notebook URL")
            print(f"   2. Check the output for where the model was saved")
            print(f"   3. Download the nemotron_lora_adapter directory from the notebook output")

        return True

    except Exception as e:
        print(f"❌ Error retrieving adapter: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    print("🚀 NEMOTRON ADAPTER RETRIEVAL")
    print("=" * 50)

    # Check both notebooks, prioritize the improved one
    notebooks = [
        "nemotron-lora-baseline-improved-manderson240",
        "nemotron-lora-baseline-manderson240",
    ]

    for notebook in notebooks:
        print(f"\n📋 Attempting to retrieve from: {notebook}")
        success = await retrieve_trained_adapter(notebook)
        if success:
            print(f"✅ Successfully initiated retrieval from {notebook}")
            break
        else:
            print(f"❌ Failed to retrieve from {notebook}")
            print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
