"""Unit tests for hardened AutoHarness AST Action Security Validator."""

from __future__ import annotations

from cohezion.actioner.autoharness_verifier import verify_ast_action_safety


def test_safe_action_code() -> None:
    code = """
def add_vectors(a: list, b: list) -> list:
    return [x + y for x, y in zip(a, b)]
"""
    assert verify_ast_action_safety(code) is True


def test_block_builtins_and_dict_traversal() -> None:
    code = """
payload = __builtins__.__dict__['__import__']('os').system
"""
    assert verify_ast_action_safety(code) is False


def test_block_subclasses_traversal() -> None:
    code = """
subclasses = ().__class__.__bases__[0].__subclasses__()
"""
    assert verify_ast_action_safety(code) is False


def test_block_memory_exhaustion_multiplication() -> None:
    code = """
payload = [0] * 10000000
"""
    assert verify_ast_action_safety(code) is False
