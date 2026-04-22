# tests/test_graph_write_tools.py
import os
import sys
from unittest.mock import MagicMock

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mcp_server.graph_write_tools import (
    GraphWriteError,
    _validate_not_explicit_synapse,
    build_affinity_update_sql,
    build_annotate_sql,
    build_latent_synapse_sql,
)


def test_latent_synapse_sql_format():
    sql = build_latent_synapse_sql("neuron:abc", "neuron:xyz", "test reason")
    assert "RELATE" in sql
    assert "neuron:abc" in sql
    assert "neuron:xyz" in sql
    assert "'latent'" in sql


def test_affinity_update_sql():
    vec = [0.1] * 12
    sql = build_affinity_update_sql("neuron:abc", vec)
    assert "UPDATE neuron:abc" in sql
    assert "dim_agent_affinity" in sql


def test_annotate_sql_only_safe_fields():
    sql = build_annotate_sql("neuron:abc", last_accessed="2026-01-01", agent_notes="test")
    assert "last_accessed" in sql
    assert "agent_notes" in sql
    # Must not touch structural fields
    assert "title" not in sql
    assert "path" not in sql


def test_validate_not_explicit_raises():
    mock_client = MagicMock()
    mock_client.query.return_value = [{"result": [{"type": "explicit"}]}]
    with pytest.raises(GraphWriteError, match="explicit synapse"):
        _validate_not_explicit_synapse(mock_client, "neuron:a", "neuron:b")


def test_validate_not_explicit_passes_when_empty():
    mock_client = MagicMock()
    mock_client.query.return_value = [{"result": []}]
    # Should not raise
    _validate_not_explicit_synapse(mock_client, "neuron:a", "neuron:b")
