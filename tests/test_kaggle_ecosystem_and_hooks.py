"""Unit tests for Cohezion Kaggle Ecosystem Leverage and Hook Triggers.
========================================================================
Validates that Cohezion is fully wired to leverage:
1. `kagglesdk`: Typed RPC APIs and event publishing.
2. `kagglehub`: Zero-copy asset management and resource sync events.
3. `docker-python`: Automated import verification against Kaggle container specs.
4. `EventBus`: Kaggle ecosystem event schemas and publication lifecycle.
5. `.omg/state/hooks.json`: Active signal registrations.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from cohezion.core.event_bus import Event, EventBus, EventType
from scripts.hooks.docker_python_verifier import verify_file, extract_imports_from_source


@pytest.mark.asyncio
async def test_event_bus_kaggle_ecosystem_events():
    """Verify that EventBus handles all new Kaggle ecosystem events."""
    bus = EventBus()
    received_events = []

    @bus.subscribe(EventType.KAGGLE_RESOURCE_SYNCED)
    async def on_resource_sync(event: Event):
        received_events.append(event)

    @bus.subscribe(EventType.KAGGLE_BENCHMARK_RECORDED)
    async def on_benchmark(event: Event):
        received_events.append(event)

    @bus.subscribe(EventType.KAGGLE_AGENT_EXAM_EVALUATED)
    async def on_agent_exam(event: Event):
        received_events.append(event)

    await bus.start()

    # Publish resource sync event
    ev1 = Event.kaggle_resource_synced(
        resource_type="model",
        handle="google/gemma-2/transformers/2b-it",
        local_path="/cache/models/gemma-2b",
    )
    await bus.publish(ev1)

    # Publish benchmark event
    ev2 = Event.kaggle_benchmark_recorded(
        task_name="arc_agi_autoharness_verifier",
        metric_value=0.885,
        run_id="run_20261012_001",
    )
    await bus.publish(ev2)

    # Publish agent exam event
    ev3 = Event.kaggle_agent_exam_evaluated(
        exam_id="sae_2026_q4",
        score=94.5,
        details={"accuracy": 0.945, "latency_sec": 4.2},
    )
    await bus.publish(ev3)

    await bus.stop()

    assert len(received_events) == 3
    assert received_events[0].payload["handle"] == "google/gemma-2/transformers/2b-it"
    assert received_events[1].payload["metric_value"] == 0.885
    assert received_events[2].payload["score"] == 94.5


def test_hooks_json_signals():
    """Verify that .omg/state/hooks.json has active signals for Kaggle resources."""
    hooks_path = Path(".omg/state/hooks.json")
    assert hooks_path.exists(), "hooks.json must exist"

    with open(hooks_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    signals = data.get("derived_signals", {})
    assert signals.get("docker-python-verifier") is True
    assert signals.get("kagglesdk-typed-bridge") is True
    assert signals.get("kagglehub-zero-copy-guard") is True
    assert signals.get("kaggle-benchmarks-evaluator") is True
    assert signals.get("kaggle-agent-exam-validator") is True


def test_docker_python_verifier_extracts_imports(tmp_path):
    """Test AST import extraction on synthetic code."""
    source = """
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import nonexistent_obscure_lib_xyz_123
"""
    imports = extract_imports_from_source(source)
    assert "numpy" in imports
    assert "pandas" in imports
    assert "scipy" in imports
    assert "nonexistent_obscure_lib_xyz_123" in imports

    test_file = tmp_path / "test_kernel.py"
    test_file.write_text(source, encoding="utf-8")

    ok, missing = verify_file(test_file)
    assert ok is False
    assert "nonexistent_obscure_lib_xyz_123" in missing


def test_docker_python_verifier_passes_valid_code(tmp_path):
    """Test AST import verification on valid Kaggle docker-python packages."""
    source = """
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score
import lightgbm as lgb
from rdkit import Chem
"""
    test_file = tmp_path / "valid_kernel.py"
    test_file.write_text(source, encoding="utf-8")

    ok, missing = verify_file(test_file)
    assert ok is True
    assert len(missing) == 0
