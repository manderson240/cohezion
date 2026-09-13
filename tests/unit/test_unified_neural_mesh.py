"""Unit tests for UnifiedLocalNeuralMesh Engine.

Verifies end-to-end routing across associative neurons, silicon compute,
and deterministic AST validation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.inference.unified_neural_mesh import NeuralMeshResponse, UnifiedNeuralMesh


@pytest.fixture
def mesh():
    return UnifiedNeuralMesh()


def test_ast_verification_valid_code(mesh):
    valid_code = """def is_alive():
    return True"""
    assert mesh._verify_ast_safety(valid_code) is True


def test_ast_verification_invalid_code(mesh):
    invalid_code = """def broken(:
    return True"""
    assert mesh._verify_ast_safety(invalid_code) is False


def test_ast_verification_markdown_wrapped_code(mesh):
    markdown_code = """Here is the code:
```python
def greet(name):
    return f'Hello, {name}'
```"""
    assert mesh._verify_ast_safety(markdown_code) is True


@pytest.mark.asyncio
async def test_generate_unified_response_mocked():
    mesh = UnifiedNeuralMesh()
    with (
        patch.object(mesh, "fetch_associative_neurons", return_value=["Neuron: Port 8001 DB"]),
        patch.object(
            mesh,
            "_query_endpoint",
            return_value="""```python
def test_fn():
    return 'mesh'
```""",
        ),
    ):
        res = await mesh.generate_unified_response("Write a test function")
        assert isinstance(res, NeuralMeshResponse)
        assert res.ast_verified is True
        assert res.retrieved_neurons == ["Neuron: Port 8001 DB"]
        assert "test_fn" in res.unified_output
