import json

import pytest

from cohezion.integrations.kaggle_training import KaggleTrainingManager


def test_generate_lora_config():
    """Test generating LoRA configuration."""
    manager = KaggleTrainingManager()
    config = manager.generate_lora_config(r=8, alpha=16, target_modules=["x_proj", "embeddings"])
    
    assert config["r"] == 8
    assert config["lora_alpha"] == 16
    assert "x_proj" in config["target_modules"]
    assert config["peft_type"] == "LORA"

def test_generate_adapter_config():
    """Test generating adapter_config.json."""
    manager = KaggleTrainingManager()
    adapter_config = manager.generate_adapter_config(base_model_name="nvidia/Nemotron-3-Nano-30B-A3B")
    
    assert adapter_config["base_model_name_or_path"] == "nvidia/Nemotron-3-Nano-30B-A3B"
    assert "peft_type" in adapter_config

@pytest.mark.asyncio
async def test_prepare_kaggle_notebook(tmp_path):
    """Test preparing the Kaggle notebook with training code."""
    manager = KaggleTrainingManager()
    output_path = tmp_path / "training_notebook.ipynb"
    
    await manager.prepare_notebook(
        code="print('training...')",
        output_path=output_path
    )
    
    assert output_path.exists()
    with open(output_path, "r") as f:
        notebook = json.load(f)
        assert notebook["cells"][0]["source"][0] == "print('training...')"
