#!/usr/bin/env python3
"""
RAG Query Tool — Kernel Optimization Research Assistant

Uses local Ollama models + embedding retrieval to answer
GPU kernel optimization questions.

Combines:
- Long-context Ollama inference (qwen2.5-coder:14b, 128K ctx)
- ChromaDB pattern retrieval
- Chain-of-thought reasoning (deepseek-r1:7b)

Usage:
    python rag_query.py "How do I optimize MLA attention?"
    python rag_query.py --model deepseek-r1 "Why is MFMA faster than LUT?"
    python rag_query.py --interactive
"""

import argparse
import sys
from pathlib import Path


# Add local_models to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from embeddings import KernelEmbedder
    from local_model_manager import OllamaManager

    MANAGER_AVAILABLE = True
except ImportError as e:
    MANAGER_AVAILABLE = False
    print(f"Warning: {e}")


SYSTEM_PROMPT = """You are an expert GPU kernel optimization researcher specializing in:
- AMD CDNA 3 architecture (MI355X)
- CUDA/HIP kernel development
- MFMA instruction optimization
- LLM inference optimization (GEMM, MoE, MLA attention)

You have access to a database of successful kernel optimization patterns.
Use these patterns to provide specific, actionable recommendations.

When answering:
1. Reference specific successful patterns
2. Provide concrete code examples
3. Explain the performance impact
4. Note any risks or tradeoffs
"""


class RAGQuery:
    """Retrieval-augmented generation for kernel optimization."""

    def __init__(
        self,
        embedder: KernelEmbedder = None,
        model: str = "qwen2.5-coder:14b",
        reasoner: str = "deepseek-r1:7b",
    ):
        self.embedder = embedder
        self.model = model
        self.reasoner = reasoner

        if MANAGER_AVAILABLE:
            self.ollama = OllamaManager()
        else:
            self.ollama = None

        # Prompt templates
        self.rag_template = """## CONTEXT: Retrieved Patterns

{patterns}

---

## QUESTION: {question}

Provide a detailed answer using the retrieved patterns. Include specific code recommendations and expected performance improvements.
"""

        self.reasoning_template = """## QUESTION: {question}

## CONTEXT:
{patterns}

## REASONING (think step by step):
{reasoning}

Now provide your final answer:
"""

    def retrieve_patterns(self, query: str, top_k: int = 5, category: str = None) -> list[dict]:
        """Retrieve relevant patterns from the embedding database."""
        if self.embedder is None:
            print("Warning: Embedder not available, skipping retrieval")
            return []

        try:
            results = self.embedder.query(query, top_k=top_k, category=category)
            return results
        except Exception as e:
            print(f"Retrieval failed: {e}")
            return []

    def _format_patterns(self, patterns: list[dict]) -> str:
        """Format retrieved patterns for prompt."""
        if not patterns:
            return "No relevant patterns found in database."

        formatted = []
        for i, p in enumerate(patterns, 1):
            formatted.append(f"""### Pattern {i}: {p["id"]}
**Category:** {p["metadata"].get("category", "unknown")}
**Outcome:** {p["metadata"].get("outcome", "unknown")}

{p["document"][:800]}
---""")

        return "\n\n".join(formatted)

    def query(
        self,
        question: str,
        use_retrieval: bool = True,
        use_reasoning: bool = False,
        category: str = None,
    ) -> str:
        """
        Query with retrieval-augmented generation.

        Args:
            question: The question to answer
            use_retrieval: Whether to retrieve patterns
            use_reasoning: Whether to use chain-of-thought reasoning
            category: Filter patterns by kernel type (mla/gemm/moe)
        """
        # Step 1: Retrieve relevant patterns
        patterns = []
        if use_retrieval and self.embedder:
            patterns = self.retrieve_patterns(question, category=category)

        # Step 2: Format context
        pattern_context = self._format_patterns(patterns)

        if use_reasoning and self.reasoner:
            # Use chain-of-thought reasoning
            return self._query_with_reasoning(question, pattern_context)
        else:
            # Direct generation
            return self._generate(question, pattern_context)

    def _generate(self, question: str, pattern_context: str) -> str:
        """Generate response using Ollama."""
        if self.ollama is None:
            return "Ollama not available. Install dependencies: pip install psutil"

        prompt = self.rag_template.format(patterns=pattern_context, question=question)

        response = self.ollama.generate(
            model=self.model,
            prompt=prompt,
            context=131072,  # 128K context
            system=SYSTEM_PROMPT,
            temperature=0.7,
        )

        return response.get("response", "No response")

    def _query_with_reasoning(self, question: str, pattern_context: str) -> str:
        """Query with chain-of-thought reasoning."""
        if self.ollama is None:
            return "Ollama not available"

        # First pass: reasoning
        reasoning_prompt = f"""Think step by step about this kernel optimization question:

{question}

Given these patterns:
{pattern_context[:2000]}

Provide a brief chain-of-thought analysis (3-5 sentences):
"""

        reasoning_response = self.ollama.generate(
            model=self.reasoner, prompt=reasoning_prompt, context=131072, temperature=0.6
        )

        reasoning = reasoning_response.get("response", "")

        # Second pass: final answer
        prompt = self.reasoning_template.format(
            question=question, patterns=pattern_context, reasoning=reasoning
        )

        final_response = self.ollama.generate(
            model=self.model, prompt=prompt, context=131072, system=SYSTEM_PROMPT, temperature=0.7
        )

        return f"## Reasoning\n{reasoning}\n\n## Answer\n{final_response.get('response', '')}"


def interactive_mode(rag: RAGQuery):
    """Interactive RAG query mode."""
    print("\n" + "=" * 60)
    print("GPU Kernel Optimization Research Assistant")
    print("=" * 60)
    print(f"Model: {rag.model}")
    print(f"Reasoner: {rag.reasoner}")
    print("Type 'exit' to quit, 'context' to see retrieved patterns\n")

    while True:
        try:
            question = input("\n> ")

            if question.lower() in ("exit", "quit", "q"):
                break

            if question.lower() == "context":
                # Show recent context
                print("\nNo context tracking in this mode. Start a new query.")
                continue

            if not question.strip():
                continue

            print("\nThinking...")
            answer = rag.query(question)
            print(f"\n{answer}")

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")


def main():
    parser = argparse.ArgumentParser(description="RAG Query Tool")
    parser.add_argument("query", nargs="?", help="Query string")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--model", default="qwen2.5-coder:14b", help="Generation model")
    parser.add_argument("--reasoner", default="deepseek-r1:7b", help="Reasoning model")
    parser.add_argument("--no-retrieval", action="store_true", help="Skip retrieval")
    parser.add_argument(
        "--reasoning", "-r", action="store_true", help="Use chain-of-thought reasoning"
    )
    parser.add_argument("--category", choices=["mla", "gemm", "moe"], help="Filter by kernel type")
    parser.add_argument("--top-k", type=int, default=5, help="Number of patterns to retrieve")

    args = parser.parse_args()

    # Initialize RAG
    try:
        embedder = KernelEmbedder()
    except Exception as e:
        print(f"Warning: Could not initialize embedder: {e}")
        embedder = None

    rag = RAGQuery(embedder=embedder, model=args.model, reasoner=args.reasoner)

    if args.interactive:
        interactive_mode(rag)
    elif args.query:
        print(f"\nQuery: {args.query}")
        print(f"Model: {args.model}")
        print(f"Retrieval: {not args.no_retrieval}")
        print(f"Reasoning: {args.reasoning}")
        print()

        answer = rag.query(
            question=args.query,
            use_retrieval=not args.no_retrieval,
            use_reasoning=args.reasoning,
            category=args.category,
        )

        print(answer)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
