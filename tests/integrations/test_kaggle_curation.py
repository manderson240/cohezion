import json
from unittest.mock import patch

import numpy as np
import pytest

from cohezion.integrations.kaggle_curation import KaggleCurator


@pytest.fixture
def mock_dataset(tmp_path):
    """Create a mock JSONL dataset."""
    data = [
        {"id": "1", "question": "What is 2+2?", "answer": "4"},
        {"id": "2", "question": "What is the capital of France?", "answer": "Paris"}
    ]
    file_path = tmp_path / "train.jsonl"
    with open(file_path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    return file_path

def test_curator_initialization():
    """Test curator initialization with FLUME encoder."""
    curator = KaggleCurator()
    assert curator.encoder is not None

@pytest.mark.asyncio
async def test_process_dataset(mock_dataset, tmp_path):
    """Test processing dataset and generating embeddings."""
    curator = KaggleCurator()
    output_path = tmp_path / "processed.jsonl"
    
    # Mock the encoder to return a fixed vector
    with patch.object(curator.encoder, 'encode') as mock_encode:
        mock_encode.return_value = np.zeros(256, dtype=np.float32)
        
        await curator.process_dataset(mock_dataset, output_path)
        
        assert output_path.exists()
        with open(output_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == 2
            first_item = json.loads(lines[0])
            assert "embedding" in first_item
            assert len(first_item["embedding"]) == 256
            assert first_item["question"] == "What is 2+2?"

def test_prepare_finetuning_data(mock_dataset, tmp_path):
    """Test preparing data for LoRA fine-tuning format."""
    curator = KaggleCurator()
    output_path = tmp_path / "lora_train.jsonl"
    
    curator.prepare_finetuning_data(mock_dataset, output_path)
    
    assert output_path.exists()
    with open(output_path, "r") as f:
        line = json.loads(f.readline())
        assert "instruction" in line
        assert "output" in line
        assert "\\boxed{" in line["output"]
