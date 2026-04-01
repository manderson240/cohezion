#!/usr/bin/env python3
"""
Submit trained LoRA adapter to NVIDIA Nemotron Model Reasoning Challenge.
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


async def submit_adapter_to_competition(adapter_path: Path, message: str = None):
    """Submit the trained LoRA adapter to the Kaggle competition."""
    if not username or not api_token:
        print("❌ Missing KAGGLE_USERNAME or KAGGLE_API_TOKEN in .env")
        return False

    if not adapter_path.exists():
        print(f"❌ Adapter path does not exist: {adapter_path}")
        return False

    print(f"📤 Submitting adapter to competition: {adapter_path}")

    api = KaggleAPI(username=username, key=api_token)

    try:
        # Default message if none provided
        if message is None:
            message = f"Nemotron LoRA adapter submission from Cohezion - {username}"

        # Submit to competition
        competition_id = "nvidia-nemotron-model-reasoning-challenge"
        result = await api.submit_adapter(competition_id, adapter_path, message)

        print(f"✅ Adapter submitted successfully!")
        print(f"📊 Result: {result}")

        # Provide information about where to check results
        print(f"🔗 Check your submission at:")
        print(f"   https://www.kaggle.com/competitions/{competition_id}/submissions")

        return True

    except Exception as e:
        print(f"❌ Error submitting adapter: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    print("🚀 NEMOTRON ADAPTER SUBMISSION")
    print("=" * 50)

    # Look for trained adapters in common locations
    possible_adapter_paths = [
        Path("data/retrieved_nemotron-lora-baseline-improved-manderson240/nemotron_lora_adapter"),
        Path("data/retrieved_nemotron-lora-baseline-manderson240/nemotron_lora_adapter"),
        Path("nemotron_lora_adapter"),  # Current directory
        Path("./nemotron_lora_adapter"),
    ]

    adapter_found = False
    for adapter_path in possible_adapter_paths:
        if adapter_path.exists():
            print(f"📋 Found adapter at: {adapter_path.absolute()}")
            adapter_found = True

            success = await submit_adapter_to_competition(adapter_path)
            if success:
                print(f"✅ Submission completed successfully!")
                break
            else:
                print(f"❌ Submission failed!")
                break

    if not adapter_found:
        print("📋 No trained adapter found in expected locations.")
        print("💡 Make sure to:")
        print("   1. Wait for training to complete")
        print("   2. Run the retrieval script to get the adapter")
        print("   3. Then run this submission script")
        print("")
        print("🔍 Expected adapter location pattern:")
        print("   data/retrieved_<notebook_name>/nemotron_lora_adapter/")


if __name__ == "__main__":
    asyncio.run(main())
