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


def test_phoenix_architecture_with_custom_spec_and_evidence_bundle():
    from cohezion.agi.phoenix_architecture import SpecificationIR

    engine = PhoenixArchitectureEngine()
    custom_spec = SpecificationIR(
        name="custom_math_spec",
        intent="Calculate square of input",
        guarantees=["returns square of float"],
    )
    engine.register_specification(custom_spec)

    def custom_synthesizer(spec: SpecificationIR) -> str:
        return "def square_val(x: float) -> float:\n    return x * x\n"

    def custom_oracle(code_str: str) -> bool:
        namespace = {}
        exec(code_str, namespace)
        return namespace["square_val"](4.0) == 16.0

    res = engine.execute_deletion_and_rebirth(
        module_name="cohezion.math.square",
        specification_name="custom_math_spec",
        failing_code="def broken_square(:",
        synthesizer_fn=custom_synthesizer,
        test_oracle_fn=custom_oracle,
    )

    assert res.verified_by_oracle is True
    assert res.canary_passed is True
    assert res.rollback_occurred is False
    assert res.evidence_bundle is not None
    assert res.evidence_bundle.passed_all_gates is True
    assert res.evidence_bundle.oracle_results["custom_oracle"] is True


def test_phoenix_architecture_ast_security_violation_triggers_rollback():
    from cohezion.agi.phoenix_architecture import SpecificationIR

    engine = PhoenixArchitectureEngine()

    # Synthesizer that attempts forbidden code execution
    def malicious_synthesizer(spec: SpecificationIR) -> str:
        return "import os\ndef attack():\n    eval('2 + 2')\n"

    res = engine.execute_deletion_and_rebirth(
        module_name="cohezion.unsafe.module",
        specification_name="grid_bounds",
        failing_code="original_unbroken_code = 1",
        synthesizer_fn=malicious_synthesizer,
    )

    # Rollback must occur and failing/original code preserved
    assert res.verified_by_oracle is False
    assert res.ast_safe is False
    assert res.rollback_occurred is True
    assert res.canary_passed is False
    assert res.code_regenerated == "original_unbroken_code = 1"
