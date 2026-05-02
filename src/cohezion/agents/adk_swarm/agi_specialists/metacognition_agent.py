from google import adk


class MetacognitionAgent(adk.Agent):
    """Specialist in identifying hidden assumptions and epistemic uncertainty."""

    def __init__(self, **kwargs):
        super().__init__(
            name="MetacognitionSpecialist",
            instructions=(
                "You are an expert in cognitive science and logic. "
                "Your goal is to evaluate models on 'epistemic humility' tasks. "
                "Analyze problems for hidden assumptions, missing variables, or vagueness. "
                "Ensure the benchmark tasks you author are scientifically rigorous."
            ),
            **kwargs,
        )


agent = MetacognitionAgent()
