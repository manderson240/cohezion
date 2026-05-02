import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import polars as pl
import torch


# Ensure we can import from the kernel directory
sys.path.append(os.path.join(os.getcwd(), "sandbox/aimo/kaggle_kernel"))

import submission_transformers


class TestAIMOSubmission(unittest.TestCase):
    def setUp(self):
        # Reset global state in the module
        submission_transformers._model = MagicMock()
        submission_transformers._tokenizer = MagicMock()
        # Mock tokenizer to return a dict with tensors
        submission_transformers._tokenizer.return_value = {
            "input_ids": torch.tensor([[1, 2, 3]]),
            "attention_mask": torch.tensor([[1, 1, 1]]),
        }
        submission_transformers._start_time = None
        submission_transformers._problems_solved = 0

    def test_predict_output_format(self):
        """Verifies that predict returns a valid Polars DataFrame."""
        id_df = pl.Series(["d0"])
        problem_df = pl.Series(["Find X: 2X = 8"])

        # Mock the swarm logic to return a specific answer
        with patch("submission_transformers.specialist_team") as mock_team:
            # Note: in Python mock, return_value is the instance
            instance = mock_team.return_value
            instance.run_swarm.return_value = 4

            result = submission_transformers.predict(id_df, problem_df)

            self.assertIsInstance(result, pl.DataFrame)
            self.assertEqual(result.shape, (1, 2))
            self.assertEqual(result["id"][0], "d0")
            self.assertEqual(result["answer"][0], 4)

    def test_consensus_logic(self):
        """Tests the majority voting consensus."""
        from submission_transformers import specialist_team

        mock_model = MagicMock()
        mock_tokenizer = MagicMock()

        # Mock tokenizer to return a dict with tensors
        mock_tokenizer.return_value = {
            "input_ids": torch.tensor([[1, 2, 3]]),
            "attention_mask": torch.tensor([[1, 1, 1]]),
        }

        # Simulate 3 different answers: 42, 42, 7
        p1 = "The answer is \\boxed{42}."
        p2 = "Final result: \\boxed{42}"
        p3 = "Calculation: 7. Final answer \\boxed{7}."

        # Setup the mock team
        team = specialist_team(mock_model, mock_tokenizer)
        # Mock the generate call to return 3 sequences
        # We need to mock the decode too
        mock_tokenizer.decode.side_effect = [p1, p2, p3]

        # Mock model.generate to return a list of 3 tensors
        mock_model.generate.return_value = [torch.tensor([1]), torch.tensor([2]), torch.tensor([3])]

        # On AMD ROCm hardware, torch.cuda.is_available() returns True (ROCm presents
        # as CUDA). Without this mock, run_swarm calls v.to("cuda") which triggers a
        # GPU page fault (SIGSEGV) during consensus testing. Force CPU for this unit test.
        with patch("submission_transformers.torch.cuda.is_available", return_value=False):
            ans = team.run_swarm("Problem Text", budget=400.0)
        self.assertEqual(ans, 42, "Consensus should choose the majority answer.")


if __name__ == "__main__":
    unittest.main()
