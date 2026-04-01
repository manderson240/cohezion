import json
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import generate_evo_hiho_tasks
import pytest


@pytest.mark.asyncio
async def test_generate_batch_output_schema():
    # Mock CompoundSessionManager
    mock_mgr_instance = MagicMock()
    mock_alignment = MagicMock()
    mock_alignment.should_proceed = True
    mock_mgr_instance.check_alignment.return_value = mock_alignment
    
    # Mocked LLM output returning our desired schema
    mock_result = {
        "input": "Question:\n[Mocked Input]\nOptions:\n['[A]', '[B]', '[C]', 'Insufficient Information']",
        "output": "Insufficient Information"
    }
    
    # execute_aligned is async
    mock_execute_aligned = AsyncMock()
    mock_execute_aligned.return_value = (True, mock_result)
    mock_mgr_instance.execute_aligned = mock_execute_aligned
    
    mock_mgr_class = MagicMock()
    mock_mgr_class.return_value.__aenter__.return_value = mock_mgr_instance
    
    m_open = mock_open()
    
    with patch('generate_evo_hiho_tasks.CompoundSessionManager', mock_mgr_class), \
         patch('builtins.open', m_open):
        
        await generate_evo_hiho_tasks.generate_batch(num_tasks=2)
    
    m_open.assert_called_once()
    
    written_data = "".join(call.args[0] for call in m_open().write.call_args_list)
    parsed_data = json.loads(written_data)
    
    assert "train" in parsed_data
    assert "test" in parsed_data
    assert len(parsed_data["train"]) == 1
    assert len(parsed_data["test"]) == 1
    assert parsed_data["train"][0]["input"] == mock_result["input"]
    assert parsed_data["test"][0]["output"] == mock_result["output"]
