import pytest
from cohezion.agi.phoenix_architecture import PhoenixArchitectureEngine, PhoenixRebirthResult
from cohezion.agi.regenerative_software import RegenerativeSoftwareEngine

def test_phoenix_architecture_deletion_and_rebirth():
    engine = PhoenixArchitectureEngine()
    failing_code = "def broken_syntax(: return NULL"

    res = engine.execute_deletion_and_rebirth(
        module_name="cohezion.agi.sample_contract",
        specification_name="grid_bounds",
        failing_code=failing_code,
    )

    assert isinstance(res, PhoenixRebirthResult)
    assert res.code_deleted is True
    assert "Phoenix Architecture Rebirth" in res.code_regenerated
    assert res.verified_by_oracle is True
    assert res.zk_proof.is_valid is True
    assert res.rebirth_latency_ms >= 0.0

def test_regenerative_software_engine_phoenix_integration():
    regen = RegenerativeSoftwareEngine()
    broken_code = "def invalid_code(:"
    res = regen.heal_code_snippet(broken_code)

    assert res.proof.is_valid is True
    assert "Phoenix Architecture Rebirth" in res.regenerated_code
