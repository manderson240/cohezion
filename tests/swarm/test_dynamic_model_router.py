"""Tests for swarm/dynamic_model_router.py.

Covers intelligent model selection and hardware-aware routing.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.swarm.dynamic_model_router import (
    DynamicModelRouter,
    IDEPriority,
)


@pytest.fixture
def router():
    with patch("psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.total = 128 * (1024**3)
        mock_mem.return_value.available = 100 * (1024**3)
        return DynamicModelRouter()

def test_memory_pressure(router):
    """[P0] Should calculate memory pressure correctly."""
    # 100GB available of 128GB = ~22% pressure
    pressure = router.memory_analyzer.analyze_memory_pressure()
    assert 0.2 < pressure < 0.3

@pytest.mark.asyncio
async def test_select_optimal_model_coding(router):
    """[P0] Should prioritize coding models for coding tasks."""
    request = {
        "task_type": "coding",
        "ide_priority": IDEPriority.ZED.value,
        "urgency": "medium"
    }
    model = await router.select_optimal_model(request)
    assert "coder" in model.name or "phi" in model.name

@pytest.mark.asyncio
async def test_select_optimal_model_cloud_fallback(router):
    """[P0] Should use cloud for complex reasoning if high priority."""
    request = {
        "task_type": "complex_reasoning",
        "ide_priority": IDEPriority.ANTIGRAVITY.value,
    }
    model = await router.select_optimal_model(request)
    assert model.is_cloud is True
    assert model.name == "gemini-3.0-pro"

def test_quantization_factor(router):
    """[P0] Should apply quantization speed boosts."""
    analyzer = router.memory_analyzer
    assert analyzer.get_quantization_factor("Q4_K_M") == 1.35
    assert analyzer.get_quantization_factor("Q8_0") == 1.0

def test_detect_model_template(router):
    """[P0] Should detect correct template formats."""
    tm = router.template_manager
    assert tm.detect_model_template("qwen3-7b") == "chatml"
    assert tm.detect_model_template("llama-3-8b") == "llama3"
    assert tm.detect_model_template("phi-4") == "microsoft"
