"""
Unit tests for QuantRetriever and SchemaToSkillGenerator.
Synthesized from Jon Bratseth's Vespa thesis and The New Stack agentic retrieval analysis.
"""

from cohezion.retrieval.quant_retriever import (
    QuantQuery,
    QuantRetriever,
    RetrievalItem,
)
from cohezion.retrieval.schema_to_skill import SchemaToSkillGenerator


def test_quant_query_surrealql_builder():
    retriever = QuantRetriever()

    # Query with structured filters and lexical terms
    q = QuantQuery(
        table="goal",
        structured_filters={"competition": "arc-prize-2026", "status": "active"},
        lexical_terms=["ascension", "top10"],
        limit=5,
    )
    sql = retriever.build_surrealql(q)

    assert "SELECT * FROM goal" in sql
    assert "competition = 'arc-prize-2026'" in sql
    assert "status = 'active'" in sql
    assert "title CONTAINS 'ascension'" in sql
    assert "LIMIT 5" in sql


def test_quant_query_graph_hop():
    retriever = QuantRetriever()

    q = QuantQuery(
        table="goal",
        graph_relation="->informs_goal->",
        target_id="loop_trace:run_42",
        structured_filters={"status": "active"},
        limit=3,
    )
    sql = retriever.build_surrealql(q)

    assert "SELECT * FROM loop_trace:run_42->informs_goal->goal" in sql
    assert "status = 'active'" in sql
    assert "LIMIT 3" in sql


def test_quant_retriever_multi_channel_scoring():
    mock_db = [
        {
            "id": "goal:01",
            "title": "ARC-AGI-2 Ascension Run",
            "description": "Ascending ARC score using separable CMA",
            "status": "active",
            "embedding": [0.1, 0.2, 0.9],
        },
        {
            "id": "goal:02",
            "title": "NFL Big Data Bowl",
            "description": "Tackle prediction model",
            "status": "active",
            "embedding": [0.9, 0.1, 0.1],
        },
    ]

    retriever = QuantRetriever(sql_transport=lambda query: mock_db)

    q = QuantQuery(
        table="goal",
        lexical_terms=["ARC-AGI-2"],
        query_vector=[0.1, 0.2, 0.9],
        limit=2,
    )
    items = retriever.retrieve(q)

    assert len(items) == 2
    # First item should have higher composite score due to both lexical and vector match
    assert items[0].id == "goal:01"
    assert items[0].composite_score > items[1].composite_score
    assert items[0].vector_score > 0.95


def test_early_retrieval_quality_gate():
    # 1. Empty retrieval triggers critical deficit
    report_empty = QuantRetriever.evaluate_retrieval_quality([])
    assert report_empty.is_sufficient is False
    assert report_empty.confidence_level == "CRITICAL_DEFICIT"
    assert report_empty.risk_of_context_poisoning is True

    # 2. Low-confidence retrieval triggers critical deficit
    low_item = RetrievalItem(
        id="test:01",
        table="goal",
        content={},
        composite_score=0.45,
    )
    report_low = QuantRetriever.evaluate_retrieval_quality([low_item], min_threshold=0.65)
    assert report_low.is_sufficient is False
    assert report_low.confidence_level == "CRITICAL_DEFICIT"
    assert "below safety threshold" in report_low.diagnostic_message

    # 3. High-confidence retrieval passes
    high_item = RetrievalItem(
        id="test:02",
        table="goal",
        content={},
        composite_score=0.88,
    )
    report_high = QuantRetriever.evaluate_retrieval_quality([high_item])
    assert report_high.is_sufficient is True
    assert report_high.confidence_level == "HIGH"
    assert report_high.risk_of_context_poisoning is False


def test_schema_to_skill_generator(tmp_path):
    generator = SchemaToSkillGenerator()
    skill_text = generator.generate_skill_markdown()

    assert "# SKILL: QUANT_RETRIEVAL_PRIME" in skill_text
    assert "Search Like a 2010 Quant" in skill_text
    assert "Table: `goal`" in skill_text
    assert "Table: `loop_trace`" in skill_text
    assert "Table: `agentic_contract`" in skill_text

    target_file = tmp_path / "TEST_QUANT_SKILL.md"
    written_path = generator.write_skill_file(str(target_file))
    assert written_path == str(target_file.resolve())
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == skill_text
