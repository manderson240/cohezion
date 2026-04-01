import json
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import adversarial_eval_loop
import pytest


@pytest.mark.asyncio
async def test_evaluate_task_passes():
    mock_mgr = MagicMock()
    # execute_aligned is async
    mock_execute_aligned = AsyncMock()
    
    mock_llm_result = {
        "model_response": "The answer is Insufficient Information.",
        "passed": True,
        "critique": "Correct",
        "latent_state": [0]*256
    }
    mock_execute_aligned.return_value = (True, mock_llm_result)
    mock_mgr.execute_aligned = mock_execute_aligned
    
    task = {
        "input": "Question:\nGrid: [[1,1],[1,1]]\nOptions: ['Insufficient Information']",
        "output": "Insufficient Information"
    }
    
    mock_harness = MagicMock()
    mock_harness.get_grid_embedding.return_value = np.zeros(256)
    
    result = await adversarial_eval_loop.evaluate_task(mock_mgr, task, mock_harness)
    
    assert result["adversarial_results"]["passed"] is True
    assert "latent_state" in result["adversarial_results"]

@pytest.mark.asyncio
async def test_run_adversarial_loop_integration():
    # Mock data for the benchmark file
    benchmark_data = {
        "train": [
            {"input": "[[0]]", "output": "Insufficient Information"}
        ],
        "test": []
    }
    
    m_open = mock_open(read_data=json.dumps(benchmark_data))
    
    mock_mgr_instance = MagicMock()
    # Mock result to match what evaluate_task returns
    mock_llm_result = {
        "passed": True, 
        "latent_state": [0]*256,
        "model_response": "Correct",
        "critique": "Good"
    }
    mock_mgr_instance.execute_aligned = AsyncMock(return_value=(True, mock_llm_result))
    
    mock_mgr_class = MagicMock()
    mock_mgr_class.return_value.__aenter__.return_value = mock_mgr_instance
    
    with patch("builtins.open", m_open), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("adversarial_eval_loop.CompoundSessionManager", mock_mgr_class), \
         patch("adversarial_eval_loop.FlumeGridHarness", MagicMock()):
        
        await adversarial_eval_loop.run_adversarial_loop()
        
    m_open.assert_any_call(adversarial_eval_loop.BENCHMARK_FILE)
    m_open.assert_any_call(adversarial_eval_loop.EVALUATION_OUTPUT, "w")

import numpy as np
