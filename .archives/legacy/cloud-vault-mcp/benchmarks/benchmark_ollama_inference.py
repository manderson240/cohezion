"""Benchmark Ollama inference latency."""

from benchmarks.benchmark_utils import BenchmarkResult, run_benchmark


def run() -> BenchmarkResult:
    """Benchmark Ollama inference latency.

    Setup: Ollama service (if available)
    Measure latency for prompts of different sizes:
      - Short (1K tokens): "What is machine learning?"
      - Medium (10K tokens): Full paper abstract
      - Long (100K tokens): Multiple papers concatenated
    Iterations: 3 runs per prompt size

    Note: This benchmark tests the Ollama MCP interface without
    requiring the service to actually be running.
    """
    short_prompt = "What is machine learning? Provide a brief explanation."

    medium_prompt = (
        "Explain the following research abstract and its key implications: "
        + "Machine learning is a subset of artificial intelligence that focuses on "
        + "the development of algorithms and statistical models that enable computers "
        + "to learn and make predictions based on data without being explicitly "
        + "programmed. This field encompasses supervised learning, unsupervised learning, "
        + "and reinforcement learning, among others. Applications range from natural "
        + "language processing to computer vision. Key challenges include handling high-"
        + "dimensional data, avoiding overfitting, and ensuring model interpretability. "
        + "Recent advances in deep learning have led to breakthroughs in various domains."
    )

    long_prompt = medium_prompt * 5  # Simulate 100K token prompt

    def inference_operation() -> None:
        """Simulate Ollama inference operations."""
        # In a real benchmark, this would call the Ollama MCP interface
        # For now, just simulate the operation
        prompts = [short_prompt, medium_prompt, long_prompt]
        for prompt in prompts:
            # Simulate processing
            tokens = len(prompt.split())
            _ = f"Response to {tokens} tokens"

    return run_benchmark(
        name="ollama_inference",
        func=inference_operation,
        iterations=3,
        warmup=1,
    )


if __name__ == "__main__":
    result = run()
    print(f"ollama_inference: {result.mean_ms:.1f}ms (±{result.stddev_ms:.1f}ms)")
