"""Tests for api/services/rl.py.

Covers RL policy info and step execution.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from cohezion.api.services.rl import (
    RlStepRequest,
    rl_step_service,
)


@pytest.mark.asyncio
async def test_rl_step_service():
    """[P0] Should execute single RL step."""
    mock_policy = MagicMock()
    mock_policy.get_action.return_value = (np.zeros(256), 0.0)
    
    with patch("cohezion.api.services.rl.get_rl_policy_singleton", return_value=mock_policy):
        req = RlStepRequest(state=[0.5] * 256)
        result = await rl_step_service(req)
        
        assert len(result.action) == 256
        assert result.coherence is not None

@pytest.mark.asyncio
async def test_rl_step_service_invalid_dim():
    """[P0] Should raise 422 for invalid state dimension."""
    from fastapi import HTTPException
    req = RlStepRequest(state=[0.5] * 10)
    with pytest.raises(HTTPException) as exc:
        await rl_step_service(req)
    assert exc.value.status_code == 422
