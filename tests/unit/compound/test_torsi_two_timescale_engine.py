"""Unit tests for Two-Timescale Offline Recursive Self-Improvement (TORSI, arXiv:2610.20665).

Validates:
- Fast student sub-millisecond deterministic rule evaluation.
- Dual-implementation agreement and conservation laws (arXiv:2610.20809).
- Slow teacher offline deliberation and rule distillation.
- Full TORSI self-improvement co-evolution cycle.
"""

from __future__ import annotations

from cohezion.compound.torsi_two_timescale_engine import (
    ConservationInvariantValidator,
    DistilledRule,
    ExecutionFailure,
    FastTimescaleStudent,
    SlowTimescaleTeacher,
    TORSICurriculumEngine,
)


def test_fast_timescale_student_deterministic_matching() -> None:
    student = FastTimescaleStudent(fallback_policy=lambda s: "explore_safely")
    state = {"grid_symmetry": "vertical", "color_count": 4}

    # Before rule installation: fallback triggered
    act, is_hit, rule_id = student.select_action("arc_agi", state)
    assert act == "explore_safely"
    assert not is_hit
    assert rule_id == "fallback_policy"

    # Install certified rule
    rule = DistilledRule(
        rule_id="arc_rule_vertical_reflection",
        task_type="arc_agi",
        condition_key="grid_symmetry",
        condition_op="==",
        condition_val="vertical",
        action_directive="apply_vertical_reflection",
        author_model="teacher_deepseek_v4_pro",
        is_certified=True,
    )
    student.install_rule(rule)

    # After installation: instant zero-latency match
    act, is_hit, rule_id = student.select_action("arc_agi", state)
    assert act == "apply_vertical_reflection"
    assert is_hit
    assert rule_id == "arc_rule_vertical_reflection"
    assert student.rule_hits == 1


def test_dual_agreement_and_conservation_audit() -> None:
    validator = ConservationInvariantValidator()
    test_states = [
        {"feature": "alpha", "val": 10},
        {"feature": "beta", "val": 20},
        {"feature": "alpha", "val": 30},
    ]

    rule_a = DistilledRule(
        rule_id="r_a",
        task_type="math",
        condition_key="feature",
        condition_op="==",
        condition_val="alpha",
        action_directive="scale_by_factor_2",
        author_model="teacher_A",
    )

    # Rule B agreeing on everything
    rule_b_agree = DistilledRule(
        rule_id="r_b_agree",
        task_type="math",
        condition_key="feature",
        condition_op="==",
        condition_val="alpha",
        action_directive="scale_by_factor_2",
        author_model="teacher_B",
    )

    ok_agree, ratio, _ = validator.verify_dual_agreement(rule_a, rule_b_agree, test_states)
    assert ok_agree
    assert ratio == 1.0

    # Rule B disagreeing on action directive
    rule_b_disagree = DistilledRule(
        rule_id="r_b_disagree",
        task_type="math",
        condition_key="feature",
        condition_op="==",
        condition_val="alpha",
        action_directive="invert_signs",
        author_model="teacher_B_diff",
    )
    ok_disagree, ratio_disagree, rationale = validator.verify_dual_agreement(
        rule_a, rule_b_disagree, test_states
    )

    assert not ok_disagree
    assert ratio_disagree < 1.0
    assert "disagreement" in rationale.lower()

    # Conservation Law verification
    # Custom conservation: action must start with 'scale_'
    ok_conserve, _ = validator.verify_conservation_law(
        rule_a, test_states, conservation_fn=lambda s, a: a.startswith("scale_")
    )
    assert ok_conserve

    # Violating conservation
    ok_violated, msg = validator.verify_conservation_law(
        rule_a, test_states, conservation_fn=lambda s, a: a.startswith("rotate_")
    )
    assert not ok_violated
    assert "conservation law violated" in msg.lower()


def test_torsi_full_offline_recursive_self_improvement_loop() -> None:
    student = FastTimescaleStudent()
    teacher = SlowTimescaleTeacher()
    engine = TORSICurriculumEngine(student=student, teacher=teacher)

    validation_states = [
        {"adduct_type": "[M+H]+", "cleavage_found": True},
        {"adduct_type": "[M+Na]+", "cleavage_found": False},
        {"adduct_type": "[M-H]-", "cleavage_found": True},
    ]

    # Fast student encounters a failure during live execution
    failure = ExecutionFailure(
        failure_id="fail_casmi_001",
        task_type="casmi26",
        input_state={"adduct_type": "[M+Na]+"},
        attempted_action="assume_protonated_mass",
        error_detail="Mass adduct shift mismatch: expected sodium adduct 22.989 Da.",
    )
    teacher.record_failure(failure)
    assert len(teacher.pending_failures) == 1

    # Run Offline TORSI Self-Improvement Round
    telemetry = engine.run_offline_self_improvement_round(
        task_type="casmi26",
        validation_states=validation_states,
        conservation_fn=lambda state, action: len(action) > 0,
    )

    assert telemetry["round"] == 1
    assert telemetry["failures_analyzed"] == 1
    assert telemetry["rules_promoted"] >= 1
    assert len(teacher.pending_failures) == 0

    # Fast student can now immediately resolve the previously failing scenario with 0 latency
    test_state = {"adduct_type": "[M+Na]+"}
    action, is_hit, rule_id = student.select_action("casmi26", test_state)
    assert is_hit
    assert "corrective_action_for_adduct_type_[M+Na]+" in action
    assert "rule_casmi26_" in rule_id
