import logging
from pathlib import Path
from typing import Dict, Any

from cohezion.integrations.kaggle_api import KaggleAPI
from cohezion.integrations.kaggle_curation import KaggleCurator
from cohezion.integrations.kaggle_training import KaggleTrainingManager

logger = logging.getLogger(__name__)

class KaggleSubmissionOrchestrator:
    """
    Orchestrates the full flow:
    1. Download dataset via KaggleAPI.
    2. Curate and encode dataset via KaggleCurator (FLUME).
    3. Prepare training notebook via KaggleTrainingManager.
    4. Push notebook to Kaggle for execution on G4 VMs.
    5. (Manual/Future) Retrieve adapter and submit.
    """
    
    def __init__(self, username: str, key: str):
        self.api = KaggleAPI(username=username, key=key)
        self.curator = KaggleCurator()
        self.training_manager = KaggleTrainingManager()

    async def run_baseline_flow(self, dataset_name: str, notebook_id: str) -> Dict[str, Any]:
        """
        Execute the full baseline submission flow.
        """
        # 1. Download dataset
        logger.info(f"Downloading dataset: {dataset_name}")
        raw_data = await self.api.download_dataset(dataset_name)
        
        # Save raw data temporarily
        temp_dir = Path("data/temp_kaggle")
        temp_dir.mkdir(parents=True, exist_ok=True)
        raw_path = temp_dir / "raw_train.jsonl"
        with open(raw_path, "wb") as f:
            f.write(raw_data)
            
        # 2. Curate and encode
        logger.info("Curating and encoding dataset with FLUME VAE")
        processed_path = temp_dir / "processed_train.jsonl"
        await self.curator.process_dataset(raw_path, processed_path)
        
        # 3. Prepare training notebook
        logger.info("Preparing Kaggle training notebook")
        script = self.training_manager.get_training_script_template()
        notebook_path = temp_dir / "training_notebook.ipynb"
        await self.training_manager.prepare_notebook(script, notebook_path)
        
        # 4. Push to Kaggle
        logger.info(f"Pushing notebook {notebook_id} to Kaggle")
        with open(notebook_path, "r") as f:
            notebook_code = f.read()
            
        result = await self.api.push_notebook(notebook_id, notebook_code)
        
        logger.info(f"Flow complete! Notebook pushed: {result.get('url')}")
        return result
