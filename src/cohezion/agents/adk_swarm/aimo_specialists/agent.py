from google import adk

from cohezion.sandbox.aimo.kaggle_kernel.submission_transformers import SymbolicVerifier


# Configure AIMO Algebraist Specialist
class AlgebraistAgent(adk.Agent):
    """Specialist in symbolic algebra and Python-based mathematical verification."""

    def __init__(self, **kwargs):
        super().__init__(
            name="Algebraist",
            instructions=(
                "You are an expert mathematician specializing in symbolic algebra. "
                "Your goal is to solve complex math problems using Python code and SymPy. "
                "Always wrap your executable code in triple backticks: ```python ... ```. "
                "The final answer must be a non-negative integer in \\boxed{X} format."
            ),
            **kwargs,
        )
        self.verifier = SymbolicVerifier()

    @adk.tool
    def verify_solution(self, code: str, answer: int) -> bool:
        """Verifies a mathematical answer by executing Python code.

        Args:
            code: The Python code to execute.
            answer: The integer answer to verify.
        """
        return self.verifier.verify(code, answer)


# ADK entry point for remote discovery
agent = AlgebraistAgent()
