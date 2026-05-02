from google import adk


class NumberTheoristAgent(adk.Agent):
    """Specialist in number theory, modular arithmetic, and prime properties."""

    def __init__(self, **kwargs):
        super().__init__(
            name="NumberTheorist",
            instructions=(
                "You are an expert in number theory and modular arithmetic. "
                "Solve problems involving primes, divisibility, and integer properties. "
                "Think step-by-step. Final answer in \\boxed{X} format."
            ),
            **kwargs,
        )


agent = NumberTheoristAgent()
