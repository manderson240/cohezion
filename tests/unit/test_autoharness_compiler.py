from cohezion.agi.autoharness_compiler import AutoHarnessCompiler


def test_autoharness_compiler():
    rule_expr = "len(grid) <= 30 and mass > 0"
    evaluator = AutoHarnessCompiler.compile_rule("test_rule", rule_expr)

    # Valid state
    state_valid = {"grid": [[1, 2], [3, 4]], "mass": 5.0}
    assert evaluator(state_valid) is True

    # Invalid state
    state_invalid = {"grid": [[1, 2]], "mass": -2.0}
    assert evaluator(state_invalid) is False


def test_autoharness_compiler_latency():
    rule_expr = "mass > 0 and len(grid) <= 30"
    evaluator = AutoHarnessCompiler.compile_rule("bench_rule", rule_expr)
    state = {"grid": [[1, 2]], "mass": 10.0}

    latency_us = AutoHarnessCompiler.benchmark_rule_latency(evaluator, state, runs=500)
    assert latency_us < 100.0  # < 100 microseconds per check
