"""Unit tests for Lukyanenko Index Alignment and Metric Objective Invariants."""

import pytest
from cohezion.compound.invariant_factory import (
    AutoHarnessInvariantFactory,
    InvariantSeverity,
    LukyanenkoIndexAlignmentInvariant,
    LukyanenkoMetricInvariant,
)


def test_lukyanenko_index_alignment_catches_unverified_submission():
    raw_code = """
import pandas as pd
test = pd.read_csv("test.csv")
preds = [0.5] * len(test)
sub = pd.DataFrame({"StudyInstanceUID": test["StudyInstanceUID"], "prob": preds})
sub.to_csv("submission.csv", index=False)
"""
    inv = LukyanenkoIndexAlignmentInvariant()
    violations = inv.verify_ast(None, raw_code, {})
    # Should flag missing assertion on row length or IDs
    assert any(v.rule_name == "lukyanenko_index_alignment_invariant" for v in violations)


def test_lukyanenko_index_alignment_passes_with_assert_guards():
    raw_code = """
import pandas as pd
test = pd.read_csv("test.csv")
test_ids = test["StudyInstanceUID"].tolist()
preds = [0.5] * len(test)
sub = pd.DataFrame({"StudyInstanceUID": test_ids, "prob": preds})
assert sorted(sub["StudyInstanceUID"]) == sorted(test_ids)
assert len(sub) == len(test_ids)
sub.to_csv("submission.csv", index=False)
"""
    inv = LukyanenkoIndexAlignmentInvariant()
    violations = inv.verify_ast(None, raw_code, {})
    assert len(violations) == 0


def test_lukyanenko_metric_flags_unverified_pseudolabels():
    raw_code = """
import pandas as pd
df = pd.read_csv("/kaggle/input/rsna-abnormality/pseudolabeled_training_data.csv")
"""
    inv = LukyanenkoMetricInvariant()
    violations = inv.verify_ast(None, raw_code, {})
    assert any(v.severity == InvariantSeverity.P2_MODERATE for v in violations)


def test_autoharness_compilation_with_lukyanenko_invariants():
    res = AutoHarnessInvariantFactory.compile_and_verify(
        """
import pandas as pd
test_ids = ['id1', 'id2']
sub = pd.DataFrame({'StudyInstanceUID': test_ids, 'prob': [0.1, 0.9]})
assert sorted(sub['StudyInstanceUID']) == sorted(test_ids)
sub.to_csv('submission.csv', index=False)
""",
        "rsna-knee-abnormality-detection"
    )
    assert res.passed is True
    assert res.bytecode_valid is True
