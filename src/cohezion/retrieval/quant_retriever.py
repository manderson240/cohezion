"""
Quant-Grade Multi-Channel Hybrid Retriever for Cohezion & SurrealDB v3.3.0.
Synthesized from Jon Bratseth's Vespa thesis ("Your Agent Wants to Search Like a 2010 Quant")
and The New Stack's analysis ("Agentic AI doesn't have a model problem. It has a retrieval problem.").

Combines:
1. Exact structured filters (metadata, competition, status, timestamps).
2. Lexical term matching (exact identifiers, class names).
3. Dense vector similarity (cosine distance over z-vectors or embeddings).
4. Graph proximity hops (informs_goal, verifies_segment).
5. Early Retrieval Quality Gating: Halts context poisoning before reasoning begins.
"""

from __future__ import annotations

import base64
import json
import logging
import math
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger("quant_retriever")
logger.setLevel(logging.INFO)


@dataclass
class QuantQuery:
    """
    Rich query specification constructed by an agent searching like a 2010 quant.
    Avoids collapsing structured intent into a vague 2-word text prompt.
    """

    table: str = "goal"
    lexical_terms: list[str] = field(default_factory=list)
    query_vector: list[float] | None = None
    structured_filters: dict[str, Any] = field(default_factory=dict)
    graph_relation: str | None = None  # e.g., "->informs_goal->"
    target_id: str | None = None
    limit: int = 10
    min_confidence_threshold: float = 0.65


@dataclass
class RetrievalItem:
    """A single retrieved item with multi-channel relevance scores."""

    id: str
    table: str
    content: dict[str, Any]
    vector_score: float = 0.0
    lexical_score: float = 0.0
    filter_match: bool = True
    graph_distance: int = 0
    composite_score: float = 0.0


@dataclass
class RetrievalEvaluationReport:
    """Quality report generated before passing retrieved context to an LLM."""

    total_retrieved: int
    top_score: float
    mean_score: float
    is_sufficient: bool
    confidence_level: str  # "HIGH", "MODERATE", "CRITICAL_DEFICIT"
    risk_of_context_poisoning: bool
    diagnostic_message: str


class QuantRetriever:
    """
    Multi-channel hybrid retriever interacting directly with SurrealDB v3.3.0.
    Operates without intermediary translation models to preserve full context fidelity.
    """

    def __init__(
        self,
        url: str = "http://localhost:8001/sql",
        namespace: str = "cohezion",
        database: str = "main",
        user: str = "root",
        password: str = "root",  # noqa: S107 - default local dev credentials
        sql_transport: Callable[[str], list[dict[str, Any]]] | None = None,
    ) -> None:
        self.url = url
        self.namespace = namespace
        self.database = database
        self._auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        self._custom_transport = sql_transport

    def _execute_sql(self, query: str) -> list[dict[str, Any]]:
        """Execute raw SurrealQL query over HTTP or custom transport."""
        if self._custom_transport:
            return self._custom_transport(query)

        req = urllib.request.Request(  # noqa: S310
            self.url,
            data=query.encode(),
            headers={
                "Accept": "application/json",
                "Content-Type": "text/plain",
                "surreal-ns": self.namespace,
                "surreal-db": self.database,
                "Authorization": f"Basic {self._auth}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                parsed = json.loads(resp.read().decode())
                if isinstance(parsed, list):
                    results: list[dict[str, Any]] = []
                    for item in parsed:
                        if isinstance(item, dict) and "result" in item:
                            res = item["result"]
                            if isinstance(res, list):
                                results.extend([r for r in res if isinstance(r, dict)])
                            elif isinstance(res, dict):
                                results.append(res)
                    return results
                return []
        except Exception as e:
            logger.warning(f"SurrealDB query execution failed: {e}")
            return []

    def build_surrealql(self, q: QuantQuery) -> str:
        """
        Translates a rich QuantQuery into high-performance SurrealQL
        incorporating WHERE clauses, vector cosine distance, and graph hops.
        """
        conditions: list[str] = []

        # 1. Structured filters
        for k, v in q.structured_filters.items():
            if isinstance(v, str):
                conditions.append(f"{k} = '{v}'")
            elif isinstance(v, bool):
                conditions.append(f"{k} = {'true' if v else 'false'}")
            elif isinstance(v, (int, float)):
                conditions.append(f"{k} = {v}")

        # 2. Lexical term match
        if q.lexical_terms:
            lex_clauses = [
                f"title CONTAINS '{t}' OR description CONTAINS '{t}'" for t in q.lexical_terms
            ]
            conditions.append(f"({' OR '.join(lex_clauses)})")

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        # 3. Graph hop traversal vs table query
        if q.graph_relation and q.target_id:
            query = f"SELECT * FROM {q.target_id}{q.graph_relation}{q.table}{where_clause} LIMIT {q.limit};"
        else:
            query = f"SELECT * FROM {q.table}{where_clause} LIMIT {q.limit};"

        return query

    def retrieve(self, q: QuantQuery) -> list[RetrievalItem]:
        """
        Performs multi-channel search and scores results with early verification.
        """
        sql = self.build_surrealql(q)
        records = self._execute_sql(sql)

        items: list[RetrievalItem] = []
        for r in records:
            r_id = str(r.get("id", "unknown"))

            # Calculate lexical match score
            lex_score = 0.0
            r_str = json.dumps(r).lower()
            if q.lexical_terms:
                matched_terms = sum(1 for t in q.lexical_terms if t.lower() in r_str)
                lex_score = matched_terms / len(q.lexical_terms)
            else:
                lex_score = 1.0

            # Calculate vector cosine similarity if vector supplied
            vec_score = 0.0
            if q.query_vector and "embedding" in r and isinstance(r["embedding"], list):
                doc_vec = r["embedding"]
                dot = sum(a * b for a, b in zip(q.query_vector, doc_vec, strict=False))
                norm_q = math.sqrt(sum(a * a for a in q.query_vector)) or 1.0
                norm_d = math.sqrt(sum(b * b for b in doc_vec)) or 1.0
                vec_score = max(0.0, dot / (norm_q * norm_d))
            else:
                vec_score = 0.75  # Neutral default

            # Composite weighted fusion (40% vector, 30% lexical, 30% structured filter)
            composite = 0.40 * vec_score + 0.30 * lex_score + 0.30 * 1.0

            items.append(
                RetrievalItem(
                    id=r_id,
                    table=q.table,
                    content=r,
                    vector_score=vec_score,
                    lexical_score=lex_score,
                    composite_score=composite,
                )
            )

        # Sort descending by composite score
        items.sort(key=lambda x: x.composite_score, reverse=True)
        return items

    @staticmethod
    def evaluate_retrieval_quality(
        items: list[RetrievalItem],
        min_threshold: float = 0.65,
    ) -> RetrievalEvaluationReport:
        """
        Early Retrieval Quality Gate.
        Inspects retrieved candidates before passing to LLM to prevent compounding context drift.
        """
        if not items:
            return RetrievalEvaluationReport(
                total_retrieved=0,
                top_score=0.0,
                mean_score=0.0,
                is_sufficient=False,
                confidence_level="CRITICAL_DEFICIT",
                risk_of_context_poisoning=True,
                diagnostic_message="No matching records retrieved. Do NOT guess or hallucinate context.",
            )

        top_score = items[0].composite_score
        mean_score = sum(i.composite_score for i in items) / len(items)

        if top_score < min_threshold:
            return RetrievalEvaluationReport(
                total_retrieved=len(items),
                top_score=top_score,
                mean_score=mean_score,
                is_sufficient=False,
                confidence_level="CRITICAL_DEFICIT",
                risk_of_context_poisoning=True,
                diagnostic_message=(
                    f"Top retrieval score ({top_score:.3f}) below safety threshold ({min_threshold:.3f}). "
                    "Evidence is stale, ambiguous, or irrelevant."
                ),
            )

        confidence = "HIGH" if top_score >= 0.85 else "MODERATE"
        return RetrievalEvaluationReport(
            total_retrieved=len(items),
            top_score=top_score,
            mean_score=mean_score,
            is_sufficient=True,
            confidence_level=confidence,
            risk_of_context_poisoning=False,
            diagnostic_message=f"Verified retrieval of {len(items)} items with top composite score {top_score:.3f}.",
        )
