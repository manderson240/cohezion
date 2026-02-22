"""Tests for the hybrid scoring engine."""

import pytest
from unittest.mock import patch, MagicMock
from research.pipeline import Finding


@pytest.fixture
def sample_findings():
    """Findings with varying relevance to Cohezion focus areas."""
    return [
        Finding(
            title="Building Compound AI Systems with Knowledge Graphs",
            url="https://example.com/1",
            source="web_search",
            snippet="A guide to compound AI architecture using knowledge graph memory and decision records for session persistence.",
            category="compound_engineering",
        ),
        Finding(
            title="KV Cache Optimization for Long Context LLMs",
            url="https://example.com/2",
            source="arxiv",
            snippet="We present a novel approach to KV cache compression that reduces token usage by 40% while maintaining quality.",
            category="token_efficiency",
        ),
        Finding(
            title="Best Pizza in NYC 2026",
            url="https://example.com/3",
            source="web_search",
            snippet="A review of the best pizza restaurants in New York City.",
            category="compound_engineering",
        ),
    ]


@pytest.fixture
def scoring_config():
    """Config for scoring tests."""
    return {
        "focus_areas": {
            "compound_engineering": {
                "queries": ["compound AI"],
                "weight": 1.0,
            },
            "token_efficiency": {
                "queries": ["token optimization"],
                "weight": 1.0,
            },
            "context_awareness": {
                "queries": ["context window"],
                "weight": 1.0,
            },
            "app_creation": {
                "queries": ["agentic framework"],
                "weight": 1.0,
            },
        },
        "scoring": {
            "model": "mistral:latest",
            "ollama_url": "http://localhost:11434",
            "keyword_threshold": 0,
            "top_n": 60,
        },
    }


# --- Keyword scoring ---


def test_keyword_scorer_assigns_nonzero_to_relevant(sample_findings, scoring_config):
    """Relevant findings get non-zero keyword scores."""
    from research.scorer import keyword_score

    scored = keyword_score(sample_findings, scoring_config)
    # "compound AI" + "knowledge graph" + "memory" + "decision record" => high score
    assert scored[0].raw_score > 0


def test_keyword_scorer_assigns_zero_to_irrelevant(sample_findings, scoring_config):
    """Irrelevant findings (pizza review) get zero keyword scores."""
    from research.scorer import keyword_score

    scored = keyword_score(sample_findings, scoring_config)
    pizza = [f for f in scored if "pizza" in f.title.lower()][0]
    assert pizza.raw_score == 0


def test_keyword_scorer_preserves_all_findings(sample_findings, scoring_config):
    """Keyword scorer doesn't drop any findings."""
    from research.scorer import keyword_score

    scored = keyword_score(sample_findings, scoring_config)
    assert len(scored) == len(sample_findings)


# --- Ollama scoring ---


@pytest.mark.asyncio
async def test_ollama_scorer_calls_api(sample_findings, scoring_config):
    """Ollama scorer calls the local API with scoring prompt."""
    from research.scorer import ollama_score

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "7"}

    with patch("research.scorer.requests.post", return_value=mock_resp) as mock_post:
        scored = await ollama_score(sample_findings[:1], scoring_config)
        assert mock_post.called
        assert len(scored) == 1


@pytest.mark.asyncio
async def test_ollama_scorer_fallback_when_unavailable(sample_findings, scoring_config):
    """Ollama scorer gracefully falls back when service is down."""
    from research.scorer import ollama_score

    with patch("research.scorer.requests.post", side_effect=ConnectionError("Ollama offline")):
        scored = await ollama_score(sample_findings, scoring_config)
        # Should return findings unchanged (keyword scores preserved)
        assert len(scored) == len(sample_findings)


# --- Skill candidate detection ---


def test_skill_candidate_detection(scoring_config):
    """Findings describing tools/patterns get skill_candidate flag."""
    from research.scorer import detect_skill_candidates

    findings = [
        Finding(
            title="New Python Framework for Building AI Agents",
            url="https://example.com",
            source="web_search",
            snippet="A reusable framework and template for multi-agent orchestration.",
            category="app_creation",
        ),
        Finding(
            title="Understanding Quantum Computing",
            url="https://example.com/2",
            source="web_search",
            snippet="An overview of quantum computing principles.",
            category="compound_engineering",
        ),
    ]

    result = detect_skill_candidates(findings)
    # Framework + template => skill candidate
    assert result[0].get("skill_candidate") is True
    # No skill keywords
    assert result[1].get("skill_candidate") is False


# --- Combined scoring ---


@pytest.mark.asyncio
async def test_score_returns_top_n(sample_findings, scoring_config):
    """Score function returns at most top_n findings sorted by score."""
    from research.scorer import score

    scoring_config["scoring"]["top_n"] = 2

    with patch("research.scorer.requests.post", side_effect=ConnectionError("offline")):
        scored, metadata = await score(sample_findings, scoring_config)

    assert len(scored) <= 2
    # Should be sorted descending by score
    if len(scored) >= 2:
        assert scored[0].raw_score >= scored[1].raw_score
