import os

from dotenv import load_dotenv


# MUST be first to ensure Kaggle libs find credentials
load_dotenv()
username = os.getenv("KAGGLE_USERNAME") or os.getenv("username")
api_token = os.getenv("KAGGLE_API_TOKEN")

if api_token and api_token.startswith("KGAT_"):
    api_token = api_token[5:]

if username:
    os.environ["KAGGLE_USERNAME"] = username
if api_token:
    os.environ["KAGGLE_KEY"] = api_token

import asyncio
import logging
import time

from cohezion.integrations.kaggle_api import KaggleAPI


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def watch_training():
    if not username or not api_token:
        logger.error("Missing KAGGLE_USERNAME or KAGGLE_API_TOKEN in .env")
        return

    notebook_id = f"nemotron-lora-baseline-{username.replace('_', '-')}"
    logger.info(f"Watching Kaggle training status for: {notebook_id}")
    
    api = KaggleAPI(username=username, key=api_token)
    
    last_status = None
    
    while True:
        status = await api.get_notebook_status(notebook_id)
        
        if status != last_status:
            print(f"\n[{time.strftime('%H:%M:%S')}] Status changed: {status}")
            last_status = status
            
        if status == "complete":
            print("\n" + "="*50)
            print("TRAINING COMPLETE! LoRA adapter is ready.")
            print("="*50)
            print(f"URL: https://www.kaggle.com/{username}/{notebook_id}")
            print("="*50)
            break
        elif status in ["error", "cancelAck", "cancelRequested"]:
            print(f"\nTraining stopped with status: {status}")
            break
            
        # Poll every 5 minutes
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(watch_training())
