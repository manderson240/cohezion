"""Tests for api/services/skills.py.

Covers PRIME skill parsing and spec generation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from cohezion.api.services.skills import (
    TemplateParseRequest,
    parse_template_service,
)


@pytest.mark.asyncio
async def test_parse_template_service_success():
    """[P0] Should parse skill spec successfully."""
    mock_spec = MagicMock()
    mock_spec.name = "TEST_PRIME"
    mock_spec.domain_expertise = "Test expertise"
    mock_spec.concepts = {"c1": "v1"}
    mock_spec.instructions = ["i1"]
    mock_spec.version = "1.0"
    mock_spec.see_also = []
    
    mock_manager = MagicMock()
    mock_manager.engine.get_spec_by_name.return_value = mock_spec
    mock_manager.engine.generate_agent_stub.return_value = "class TestAgent"
    mock_manager.engine.generate_config_class.return_value = "class TestConfig"
    
    with patch("cohezion.core.config_templates.ConfigTemplateManager", return_value=mock_manager):
        req = TemplateParseRequest(skill_name="TEST_PRIME")
        result = await parse_template_service(req)
        
        assert result.name == "TEST_PRIME"
        assert result.agent_stub == "class TestAgent"

@pytest.mark.asyncio
async def test_parse_template_service_not_found():
    """[P0] Should raise 404 if skill not found."""
    mock_manager = MagicMock()
    mock_manager.engine.get_spec_by_name.return_value = None
    
    with patch("cohezion.core.config_templates.ConfigTemplateManager", return_value=mock_manager):
        req = TemplateParseRequest(skill_name="NON_EXISTENT")
        with pytest.raises(HTTPException) as exc:
            await parse_template_service(req)
        assert exc.value.status_code == 404
