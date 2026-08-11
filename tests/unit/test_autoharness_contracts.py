import pytest
from cohezion.contracts import VerificationResult, CodeAsAction, PoincarePoint
from cohezion.actioner.autoharness_verifier import AutoHarnessVerifier, ExecutableAction

def test_verification_result_factory():
    res = VerificationResult.success(score=0.95, metadata={"test": True}, duration_ms=1.2)
    assert res.valid is True
    assert res.score == 0.95
    assert res.metadata["test"] is True
    assert res.duration_ms == 1.2

    fail = VerificationResult.failure(["Forbidden import"], score=0.0)
    assert fail.valid is False
    assert "Forbidden import" in fail.errors

def test_autoharness_verifier_clean_code():
    verifier = AutoHarnessVerifier()
    code = """
def safe_action(x: int, y: int) -> int:
    return x + y
"""
    res = verifier.verify_code(code)
    assert res.valid is True
    assert res.score == 1.0
    assert res.duration_ms >= 0.0

def test_autoharness_verifier_disallowed_import():
    verifier = AutoHarnessVerifier()
    code = """
import os.system
os.system('echo dangerous')
"""
    res = verifier.verify_code(code)
    assert res.valid is False
    assert any("Disallowed import" in e for e in res.errors)

def test_autoharness_verifier_eval_exec():
    verifier = AutoHarnessVerifier()
    code = "eval('2 + 2')"
    res = verifier.verify_code(code)
    assert res.valid is False
    assert any("Forbidden call" in e for e in res.errors)

def test_executable_action():
    action = ExecutableAction(name="test_action", source_code="def run(): pass")
    assert action.name == "test_action"
    res = action.verify()
    assert res.valid is True
