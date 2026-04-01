import asyncio
import logging
import os

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

# Now import the orchestrator (which imports Kaggle libs)
from cohezion.integrations.kaggle_submission import KaggleSubmissionOrchestrator


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_baseline():
    if not username or not api_token:
        logger.error("Missing KAGGLE_USERNAME or KAGGLE_API_TOKEN in .env")
        return

    logger.info(f"Starting NVIDIA Nemotron Challenge baseline flow for user: {username}")
    
    orchestrator = KaggleSubmissionOrchestrator(username=username, key=api_token)
    
    try:
        # Define competition and notebook details
        competition_id = "nvidia-nemotron-model-reasoning-challenge"
        notebook_id = f"nemotron-lora-baseline-{username.replace('_', '-')}"
        
        # Execute the full flow
        result = await orchestrator.run_baseline_flow(
            competition_id=competition_id,
            notebook_id=notebook_id
        )
        
        print("\n" + "="*50)
        print("BASELINE FLOW INITIATED SUCCESSFULLY")
        print("="*50)
        print(f"Notebook ID: {notebook_id}")
        print(f"Kaggle URL:  {result.get('url')}")
        print("="*50)
        print("The training is now running on Kaggle's G4 VM infrastructure.")
        print("Once complete, the LoRA adapter will be ready for submission.")
        
    except Exception as e:
        logger.error(f"Baseline flow failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_baseline())
