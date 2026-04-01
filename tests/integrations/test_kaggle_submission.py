from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.integrations.kaggle_submission import KaggleSubmissionOrchestrator


@pytest.mark.asyncio
async def test_orchestrate_baseline_submission(tmp_path):
    """Test the full orchestration of curation, training, and submission."""
    # Mock credentials
    username = "testuser"
    key = "testkey"
    
    # Create temp data dir
    data_dir = Path("data/temp_kaggle")
    data_dir.mkdir(parents=True, exist_ok=True)
    notebook_path = data_dir / "training_notebook.ipynb"
    
    # Mock dependencies BEFORE instantiating the orchestrator
    with patch("cohezion.integrations.kaggle_submission.KaggleAPI") as MockAPI, \
         patch("cohezion.integrations.kaggle_submission.KaggleCurator") as MockCurator, \
         patch("cohezion.integrations.kaggle_submission.KaggleTrainingManager") as MockManager:
        
        mock_api = MockAPI.return_value
        mock_curator = MockCurator.return_value
        mock_manager = MockManager.return_value
        
        # Setup mocks
        mock_api.download_dataset = AsyncMock(return_value=b"data")
        mock_curator.process_dataset = AsyncMock()
        mock_manager.get_training_script_template = MagicMock(return_value="print('training...')")
        
        # Mock prepare_notebook to actually create the file
        async def side_effect(code, path):
            with open(path, "w") as f:
                f.write(code)
        mock_manager.prepare_notebook.side_effect = side_effect
        
        mock_api.push_notebook = AsyncMock(return_value={"status": "complete", "url": "http://kaggle.com/res"})
        
        # Instantiate orchestrator
        orchestrator = KaggleSubmissionOrchestrator(username=username, key=key)
        
        # Run orchestration
        result = await orchestrator.run_baseline_flow(
            dataset_name="nvidia/nemotron-challenge",
            notebook_id="nemotron-lora-training"
        )
        
        assert result["status"] == "complete"
        mock_api.download_dataset.assert_called_once()
        mock_curator.process_dataset.assert_called_once()
        mock_manager.prepare_notebook.assert_called_once()
        mock_api.push_notebook.assert_called_once()
        
        # Cleanup
        if notebook_path.exists():
            notebook_path.unlink()
        if (data_dir / "raw_train.jsonl").exists():
            (data_dir / "raw_train.jsonl").unlink()
        if (data_dir / "processed_train.jsonl").exists():
            (data_dir / "processed_train.jsonl").unlink()
