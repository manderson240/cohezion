from database import log_hallucination


def run_example():
    """
    Runs an example of logging a hallucination.
    """
    print("Logging an example hallucination...")
    log_hallucination(
        agent_name="example_agent",
        original_request="What is the color of the sky?",
        hallucinated_output="Green",
        correction="Blue",
        notes="The agent seems to have a problem with colors.",
        metadata={"model_version": "1.1", "confidence": 0.5},
    )
    print("Example hallucination logged successfully.")


if __name__ == "__main__":
    run_example()
