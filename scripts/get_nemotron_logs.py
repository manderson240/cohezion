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

from cohezion.integrations.kaggle_api import KaggleAPI


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_logs():
    if not username or not api_token:
        logger.error("Missing KAGGLE_USERNAME or KAGGLE_API_TOKEN in .env")
        return

    notebook_id = f"nemotron-lora-baseline-improved-{username.replace('_', '-')}"
    logger.info(f"Retrieving logs for: {notebook_id}")
    
    api = KaggleAPI(username=username, key=api_token)
    
    logs = await api.get_notebook_output(notebook_id)
    
    print("\n" + "="*50)
    print(f"KAGGLE LOGS: {notebook_id}")
    print("="*50)
    print(logs)
    print("="*50)

if __name__ == "__main__":
    asyncio.run(get_logs())
