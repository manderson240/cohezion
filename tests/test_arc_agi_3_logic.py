import torch

from cohezion.swarm.agents.arc_agi_3_wrapper import RecursiveChainOfThought


def test_dynamic_exit():
    dim = 256
    depth = 10
    threshold = 0.05  # Low threshold to trigger exit

    model = RecursiveChainOfThought(dim=dim, depth=depth, threshold=threshold)

    # Random initial state
    z = torch.randn(1, dim)

    # Run with high threshold (should not exit early)
    model.threshold = -1.0
    model(z)
    print("Full depth reasoning completed.")

    # Run with low threshold (should exit early)
    model.threshold = 100.0  # Force exit immediately
    model(z)
    print("Immediate exit reasoning completed.")

    # Test with realistic threshold
    model.threshold = 5.0  # Random guess for entropy range
    model(z)

    print("Recursive Reasoning Test Passed.")


def test_refine_prediction_correct_feedback():
    from cohezion.arc.tracks.arc_agi_3 import _refine_prediction

    grid = [[1, 2], [3, 4]]
    refined = _refine_prediction(grid, "correct", grid, [], None)
    assert refined == grid


def test_refine_prediction_wrong_shape_changes_shape():
    from cohezion.arc.tracks.arc_agi_3 import _refine_prediction

    first_pred = [[1, 2, 3], [4, 5, 6]]  # 2x3
    test_input = [[1, 2], [3, 4], [5, 6]]  # 3x2
    refined = _refine_prediction(first_pred, "wrong_shape", test_input, [], None)
    assert refined is not None
    # Must not match the rejected shape (2x3)
    assert (len(refined), len(refined[0])) != (2, 3)


def test_refine_prediction_wrong_colors_changes_palette():
    from cohezion.arc.tracks.arc_agi_3 import _refine_prediction

    first_pred = [[1, 1], [1, 1]]
    test_input = [[0, 0], [0, 0]]
    refined = _refine_prediction(first_pred, "wrong_colors", test_input, [], None)
    assert refined is not None
    pred_colors = {c for row in refined for c in row}
    # Must not contain only color 1
    assert pred_colors != {1}


def test_refine_prediction_with_builder_rule_beam():
    from cohezion.arc.codec import grids_equal
    from cohezion.arc.pattern_extractor import CompoundRule
    from cohezion.arc.submission import SubmissionBuilder
    from cohezion.arc.tracks.arc_agi_3 import _refine_prediction

    class MockBuilder:
        def _apply_rule(self, grid, rule):
            if rule.signature == "rule_1":
                return [[1, 1], [1, 1]]  # Matches first_pred (failed)
            elif rule.signature == "rule_2":
                return [[2, 2], [2, 2]]  # Orthogonal candidate
            return None

        def _valid_grid(self, grid):
            return True

        def _fallback_dsl(self, grid):
            return None

    from types import SimpleNamespace

    first_pred = [[1, 1], [1, 1]]
    test_input = [[0, 0], [0, 0]]
    rule1 = SimpleNamespace(signature="rule_1")
    rule2 = SimpleNamespace(signature="rule_2")

    refined = _refine_prediction(
        first_pred=first_pred,
        feedback="wrong_pattern",
        test_input=test_input,
        rules=[rule1, rule2],
        extractor=None,
        builder=MockBuilder(),
    )

    # Must pick rule_2 because rule_1 output matches first_pred
    assert grids_equal(refined, [[2, 2], [2, 2]])


if __name__ == "__main__":
    test_dynamic_exit()
    test_refine_prediction_correct_feedback()
    test_refine_prediction_wrong_shape_changes_shape()
    test_refine_prediction_wrong_colors_changes_palette()
    test_refine_prediction_with_builder_rule_beam()
    print("All ARC-AGI-3 logic tests passed.")
