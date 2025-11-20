def execute(text):
    """
    Mock summarization function.
    In a real scenario, this would call an LLM.
    """
    if not text:
        return ""
    return f"Summary: {text[:20]}..."

metadata = {
    "name": "summarize",
    "description": "Summarizes the input text.",
    "inputs": {"text": "String to summarize"},
    "outputs": {"summary": "Summarized string"},
    "dependencies": []
}
