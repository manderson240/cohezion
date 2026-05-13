import logging
from pathlib import Path
from typing import Any

from cohezion.integrations.kaggle_api import KaggleAPI
from cohezion.integrations.kaggle_curation import KaggleCurator
from cohezion.integrations.kaggle_training import KaggleTrainingManager


logger = logging.getLogger(__name__)


class KaggleSubmissionOrchestrator:
    """
    Orchestrates the full flow:
    1. Download dataset via KaggleAPI (using kagglehub).
    2. Curate and encode dataset via KaggleCurator (FLUME).
    3. Prepare training notebook via KaggleTrainingManager.
    4. Push notebook to Kaggle for execution on G4 VMs.
    """

    def __init__(self, username: str, key: str):
        self.api = KaggleAPI(username=username, key=key)
        self.curator = KaggleCurator()
        self.training_manager = KaggleTrainingManager()

    async def run_baseline_flow(self, competition_id: str, notebook_id: str) -> dict[str, Any]:
        """
        Execute the full baseline submission flow.
        """
        # 1. Download dataset
        logger.info(f"Downloading competition data: {competition_id}")
        download_dir = await self.api.download_dataset_path(competition_id)

        # Locate the specific file (usually train.jsonl or similar)
        # For Nemotron, we'll look for a jsonl file
        jsonl_files = list(download_dir.glob("*.jsonl"))
        if not jsonl_files:
            # Fallback to look for csv or other formats if needed
            jsonl_files = list(download_dir.glob("*"))

        if not jsonl_files:
            raise FileNotFoundError(f"No data files found in {download_dir}")

        raw_data_path = jsonl_files[0]
        logger.info(f"Found data file: {raw_data_path}")

        # 2. Curate and encode
        logger.info("Curating and encoding dataset with FLUME VAE")
        temp_dir = Path("data/temp_kaggle")
        temp_dir.mkdir(parents=True, exist_ok=True)
        processed_path = temp_dir / "processed_train.jsonl"

        await self.curator.process_dataset(raw_data_path, processed_path)

        # 3. Prepare training notebook
        logger.info("Preparing Kaggle training notebook")
        script = self.training_manager.get_training_script_template()
        notebook_path = temp_dir / "training_notebook.ipynb"
        await self.training_manager.prepare_notebook(script, notebook_path)

        # 4. Push to Kaggle
        logger.info(f"Pushing notebook {notebook_id} to Kaggle")
        with open(notebook_path) as f:
            notebook_code = f.read()

        result = await self.api.push_notebook(
            notebook_id, notebook_code, competition_id=competition_id
        )

        logger.info(f"Flow complete! Notebook pushed: {result.get('url')}")
        return result
