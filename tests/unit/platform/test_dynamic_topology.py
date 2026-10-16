"""Unit tests for Dynamic Modularity Hardware Topology Manager."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from cohezion.platform.dynamic_topology import DynamicTopology


def test_dynamic_topology_defaults():
    topology = DynamicTopology.load()
    assert topology.topology_version == "2.0.0"
    assert topology.npu.enabled is True
    assert "13305" in topology.npu.endpoint
    assert topology.npu.default_model == "llama3.2-1b-FLM"
    assert topology.cpu.default_context_size == 8192
    assert topology.cpu.max_concurrent_models == 2
    assert topology.cloud.rationing_active is True


def test_dynamic_topology_environment_overrides(monkeypatch):
    monkeypatch.setenv("FLM_ENDPOINT", "http://127.0.0.1:9999/v1/chat/completions")
    monkeypatch.setenv("FLM_MODEL", "qwen3.5:4b")
    monkeypatch.setenv("LEMONADE_CTX_SIZE", "4096")
    monkeypatch.setenv("OLLAMA_CLOUD_RATIONING", "0")

    topology = DynamicTopology.load()
    assert topology.npu.endpoint == "http://127.0.0.1:9999/v1/chat/completions"
    assert topology.npu.default_model == "qwen3.5:4b"
    assert topology.cpu.default_context_size == 4096
    assert topology.cloud.rationing_active is False
    assert topology.is_cloud_fallback_allowed(is_background_task=True) is True


def test_dynamic_topology_cloud_rationing_gating(monkeypatch):
    monkeypatch.setenv("OLLAMA_CLOUD_RATIONING", "1")
    monkeypatch.setenv("OLLAMA_CLOUD_EVI_THRESHOLD", "0.85")
    monkeypatch.setenv("OLLAMA_CLOUD_ALLOW_FALLBACK", "0")

    topology = DynamicTopology.load()
    assert topology.is_cloud_fallback_allowed(is_background_task=True, evi_score=0.9) is False
    assert topology.is_cloud_fallback_allowed(is_background_task=False, evi_score=0.7) is False
    assert topology.is_cloud_fallback_allowed(is_background_task=False, evi_score=0.88) is True
