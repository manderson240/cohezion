import logging
import re


logger = logging.getLogger(__name__)


class KaggleEvaluator:
    """
    Evaluator for Kaggle reasoning challenges using LaTeX \boxed{} format.
    """

    def __init__(self):
        # Regex to find content inside \boxed{...}
        # Supports nested braces by using a recursive-like pattern if needed,
        # but for simplicity we'll start with standard non-greedy matching.
        # The competition usually expects the final boxed answer.
        self.boxed_regex = re.compile(r"\\boxed\{((?:[^{}]|\{[^{}]*\})+)\}")

    def extract_answer(self, text: str) -> str | None:
        """
        Extract the answer from the LaTeX \boxed{} command.
        If multiple \boxed{} are present, returns the last one.
        """
        matches = self.boxed_regex.findall(text)
        if not matches:
            return None
        last_match: str = matches[-1]
        return last_match.strip()

    def score(self, predictions: list[str], references: list[str]) -> dict[str, float]:
        """
        Score a list of predictions against references.
        """
        if len(predictions) != len(references):
            raise ValueError("Predictions and references must have the same length.")

        correct = 0
        total = len(predictions)

        for pred, ref in zip(predictions, references, strict=True):
            if str(pred).strip() == str(ref).strip():
                correct += 1

        accuracy = correct / total if total > 0 else 0.0

        return {"accuracy": accuracy, "correct": correct, "total": total}
