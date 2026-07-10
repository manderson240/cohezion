"""LangChain RAG tier — document QA and retrieval-augmented generation.

Wraps a LangChain chain as a TieredOrchestrator tier. Best for:
  - RAG (Retrieval-Augmented Generation) pipelines
  - Document question-answering over vault/corpus
  - Multi-step reasoning chains with structured output

Routing: use when output_type=rag_query or the task requires document retrieval.
Falls back gracefully (returns empty + error_reason) when LangChain is not installed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


def _langchain_available() -> bool:
    """True when langchain_core is importable (lazy check)."""
    try:
        import langchain_core  # noqa: F401

        return True
    except ImportError:
        return False


@dataclass
class LangChainTierResult:
    """Result from a LangChain tier invocation."""

    text: str
    primary_model: str
    latency_ms: float
    cost_usd: float = 0.0
    escalation_count: int = 0
    source_documents: list[str] = field(default_factory=list)


@dataclass
class LangChainTier:
    """LangChain chain as an inference tier.

    Parameters
    ----------
    chain : Any, optional
        A LangChain Runnable/Chain instance. If None, a default passthrough
        chain is used (returns the input unchanged — useful for testing).
    model_label : str
        Human-readable label shown in metrics (e.g. "langchain-rag").
    timeout_s : float
        Maximum seconds to wait for chain completion.
    """

    chain: Any = None
    model_label: str = "langchain-rag"
    timeout_s: float = 30.0

    def run_sync(self, prompt: str) -> tuple[str, dict]:
        """Synchronous execution — wraps async ainvoke() in asyncio.run()."""
        import asyncio

        try:
            result = asyncio.run(self.run(prompt))
            return result.text, {
                "model": result.primary_model,
                "latency_ms": result.latency_ms,
                "cost_usd": result.cost_usd,
                "local_silicon": False,
            }
        except Exception as exc:
            logger.warning("LangChainTier.run_sync failed: %s", exc)
            return "", {"error": str(exc), "model": self.model_label}

    async def run(self, prompt: str) -> LangChainTierResult:
        """Invoke the LangChain chain asynchronously.

        Falls back gracefully when LangChain is not installed.
        """
        import time

        if not _langchain_available():
            logger.debug("LangChain not installed — returning empty result")
            return LangChainTierResult(
                text="",
                primary_model=self.model_label,
                latency_ms=0.0,
                cost_usd=0.0,
            )

        chain = self.chain or _default_passthrough_chain()
        t0 = time.perf_counter()
        try:
            result = await chain.ainvoke({"input": prompt})
            elapsed_ms = (time.perf_counter() - t0) * 1000

            # Extract text from various chain output formats
            if isinstance(result, str):
                text = result
            elif isinstance(result, dict):
                text = str(result.get("output") or result.get("answer") or result.get("text") or "")
            else:
                text = str(result)

            sources = []
            if isinstance(result, dict) and "source_documents" in result:
                sources = [str(d) for d in result["source_documents"]]

            return LangChainTierResult(
                text=text,
                primary_model=self.model_label,
                latency_ms=elapsed_ms,
                source_documents=sources,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.warning("LangChainTier chain invocation failed: %s", exc)
            return LangChainTierResult(
                text="",
                primary_model=self.model_label,
                latency_ms=elapsed_ms,
                cost_usd=0.0,
            )


def _default_passthrough_chain():
    """Minimal LangChain passthrough chain for testing (requires langchain_core)."""
    try:
        from langchain_core.runnables import RunnableLambda

        return RunnableLambda(lambda x: x.get("input", "") if isinstance(x, dict) else str(x))
    except ImportError:
        return None


def build_rag_chain(
    documents: list[str] | None = None,
    llm: Any = None,
) -> LangChainTier:
    """Build a RAG chain tier from a list of document strings.

    Parameters
    ----------
    documents : list[str], optional
        Document texts to embed into the retriever. If None, returns a
        passthrough chain suitable for testing.
    llm : Any, optional
        LangChain LLM to use. If None, attempts to use the local CPU Ollama.

    Returns
    -------
    LangChainTier
        Ready-to-use tier with the configured RAG pipeline.
    """
    if not _langchain_available():
        logger.info("LangChain not installed — returning passthrough tier")
        return LangChainTier(model_label="langchain-rag-unavailable")

    if documents is None:
        return LangChainTier(
            chain=_default_passthrough_chain(), model_label="langchain-passthrough"
        )

    try:
        from langchain_community.embeddings import OllamaEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.runnables import RunnablePassthrough

        # Wiring target: fold into the tier-builder registry, or remove once confirmed
        # unreachable after integration (non-destructive-wiring policy: never a bare delete).
        embeddings = OllamaEmbeddings(
            model="phi3:mini", base_url="http://localhost:11434"
        )  # allow-direct-port: DEAD, only a test imports this module (0 prod importers)
        from langchain_core.documents import Document

        docs = [Document(page_content=d) for d in documents]
        vectorstore = FAISS.from_documents(docs, embeddings)
        retriever = vectorstore.as_retriever()

        prompt = ChatPromptTemplate.from_template(
            "Answer based on the following context:\n{context}\n\nQuestion: {question}"
        )

        chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | (llm or _default_llm())
            | StrOutputParser()
        )
        return LangChainTier(chain=chain, model_label="langchain-faiss-rag")
    except Exception as exc:
        logger.warning("RAG chain build failed, using passthrough: %s", exc)
        return LangChainTier(chain=_default_passthrough_chain(), model_label="langchain-fallback")


def _default_llm():
    """Attempt to load local Ollama as LangChain LLM (phi3:mini, free)."""
    try:
        from langchain_community.llms import Ollama

        # Wiring target: fold into the tier-builder registry, or remove once confirmed
        # unreachable after integration (non-destructive-wiring policy: never a bare delete).
        return Ollama(
            model="phi3:mini", base_url="http://localhost:11434"
        )  # allow-direct-port: DEAD, only a test imports this module (0 prod importers)
    except Exception:
        return None
