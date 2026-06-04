"""Tests for the bleeding-edge research server tools (WS4, 2026-06-03)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from cohezion.mcp.research_server import (
    _ARXIV_CATEGORIES,
    _HF_TASKS,
    ResearchMinerServer,
    _parse_arxiv_xml,
)


def test_arxiv_categories_complete():
    assert "cs.AI" in _ARXIV_CATEGORIES
    assert "cs.LG" in _ARXIV_CATEGORIES
    assert "cs.CL" in _ARXIV_CATEGORIES
    assert "cs.MA" in _ARXIV_CATEGORIES  # multiagent — for swarm program


def test_hf_tasks_complete():
    for t in ("text-generation", "image-classification", "reinforcement-learning"):
        assert t in _HF_TASKS


def test_parse_arxiv_xml_extracts_all_fields():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2402.12345v1</id>
    <title>Test Paper on HIHO Stability</title>
    <summary>Summary text here.</summary>
    <author><name>Alice</name></author>
    <author><name>Bob</name></author>
    <category term="cs.AI"/>
    <category term="cs.LG"/>
    <published>2024-02-15T00:00:00Z</published>
    <updated>2024-02-16T00:00:00Z</updated>
    <link title="pdf" href="http://arxiv.org/pdf/2402.12345v1"/>
  </entry>
</feed>"""
    parsed = _parse_arxiv_xml(xml)
    assert len(parsed) == 1
    p = parsed[0]
    assert p["id"] == "2402.12345v1"
    assert p["title"] == "Test Paper on HIHO Stability"
    assert p["authors"] == ["Alice", "Bob"]
    assert p["categories"] == ["cs.AI", "cs.LG"]
    assert p["pdf_url"] == "http://arxiv.org/pdf/2402.12345v1"


def test_parse_arxiv_xml_multiple_entries():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><id>http://arxiv.org/abs/2401.00001v1</id><title>A</title><summary>s1</summary></entry>
  <entry><id>http://arxiv.org/abs/2401.00002v1</id><title>B</title><summary>s2</summary></entry>
</feed>"""
    parsed = _parse_arxiv_xml(xml)
    assert len(parsed) == 2
    assert [p["id"] for p in parsed] == ["2401.00001v1", "2401.00002v1"]


def test_search_arxiv_advanced_rejects_unknown_category():
    s = ResearchMinerServer()
    result = s.search_arxiv_advanced(query="HIHO", category="cs.NOPE")
    assert len(result) == 1
    assert "error" in result[0]
    assert "valid_categories" in result[0]


def test_search_arxiv_advanced_builds_correct_query():
    """Verify the constructed arxiv query by stubbing the HTTP call."""
    s = ResearchMinerServer()
    captured = {}
    fake_response_xml = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"></feed>"""

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params

        class R:
            text = fake_response_xml
            status_code = 200

            def raise_for_status(self):
                pass

        return R()

    with patch("cohezion.mcp.research_server.requests.get", side_effect=fake_get):
        s.search_arxiv_advanced(
            query="multi-agent RL",
            category="cs.MA",
            date_from="20260401",
            date_to="20260430",
            limit=5,
        )
    assert captured["params"]["search_query"].startswith("all:multi-agent RL")
    assert "cat:cs.MA" in captured["params"]["search_query"]
    assert "submittedDate:[202604010000 TO 202604302359]" in captured["params"]["search_query"]
    assert captured["params"]["max_results"] == "5"


def test_search_arxiv_advanced_handles_timeout():
    s = ResearchMinerServer()
    import requests

    with patch(
        "cohezion.mcp.research_server.requests.get",
        side_effect=requests.exceptions.Timeout("nope"),
    ):
        result = s.search_arxiv_advanced(query="HIHO", category="cs.AI", limit=3)
    assert result == [{"error": "arxiv request timed out after 15s"}]


def test_get_hf_trending_models_rejects_unknown_task():
    s = ResearchMinerServer()
    result = s.get_hf_trending_models(limit=5, task="unreal-task")
    assert "error" in result[0]
    assert "valid_tasks" in result[0]


def test_list_arxiv_categories_and_hf_tasks_exposed():
    s = ResearchMinerServer()
    cats = s.list_arxiv_categories()
    assert {c["code"] for c in cats} >= {"cs.AI", "cs.LG", "cs.MA"}
    tasks = s.list_hf_tasks()
    assert "text-generation" in tasks
