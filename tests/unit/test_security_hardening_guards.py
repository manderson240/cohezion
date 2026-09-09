"""Security hardening guards (CodeQL CRITICAL fixes) — source-level unit tests.

Verifies that untrusted identifiers are validated BEFORE any external effect:
- research_server: invalid arXiv ids short-circuit before requests.get
- api.routes.rl:   invalid agent_id short-circuits before any filesystem stat
- substrate.popcorn: invalid kernel names short-circuit before subprocess.run

All external effects (HTTP, filesystem, subprocess) are mocked at source level
per AGENTS.md; no test shells out to a live binary.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import cohezion.mcp.research_server as research_server_module
from cohezion.api.routes.rl import RLPolicyResponse, get_rl_policy
from cohezion.mcp.research_server import ResearchMinerServer
from cohezion.substrate import popcorn as popcorn_module
from cohezion.substrate.popcorn import submit as popcorn_submit


# ---------------------------------------------------------------------------
# research_server: arxiv id guards must short-circuit BEFORE any HTTP request
# ---------------------------------------------------------------------------


def _no_requests_get(*_args, **_kwargs):
    raise AssertionError("requests.get must not be called for an invalid arxiv id")


def _no_sleep(*_args, **_kwargs):
    raise AssertionError("no rate-limit sleep should run on the guard path")


class TestResearchServerArxivIdGuards:
    @pytest.fixture
    def server(self) -> ResearchMinerServer:
        return ResearchMinerServer()

    @pytest.mark.parametrize("bad_id", ["../../etc", "x; rm", "2402.12345v1; rm"])
    def test_semantic_scholar_paper_rejects_invalid_arxiv_id_before_http(
        self, server, monkeypatch, bad_id
    ):
        """Invalid arxiv id returns an error dict before any requests.get."""
        monkeypatch.setattr(research_server_module.requests, "get", _no_requests_get)
        monkeypatch.setattr(research_server_module, "_arxiv_jitter", _no_sleep)
        result = server.semantic_scholar_paper(bad_id)
        assert isinstance(result, dict)
        assert "error" in result
        assert "invalid arxiv id" in result["error"]

    @pytest.mark.parametrize("bad_id", ["../../etc", "x; rm"])
    def test_papers_with_code_link_rejects_invalid_arxiv_id_before_http(
        self, server, monkeypatch, bad_id
    ):
        """Invalid arxiv id returns an error list before any requests.get."""
        monkeypatch.setattr(research_server_module.requests, "get", _no_requests_get)
        monkeypatch.setattr(research_server_module, "_arxiv_jitter", _no_sleep)
        results = server.papers_with_code_link(bad_id)
        assert isinstance(results, list)
        assert len(results) == 1
        assert "error" in results[0]
        assert "invalid arxiv id" in results[0]["error"]

    def test_semantic_scholar_paper_accepts_valid_arxiv_id_shape(self, server, monkeypatch):
        """Sanity: a well-formed id passes the guard and reaches the HTTP layer."""

        class _Resp:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"title": "t", "authors": []}

        monkeypatch.setattr(research_server_module.requests, "get", lambda *a, **k: _Resp())
        monkeypatch.setattr(research_server_module, "_arxiv_jitter", _no_sleep)
        result = server.semantic_scholar_paper("2402.12345")
        assert "error" not in result
        assert result["title"] == "t"

    def test_papers_with_code_link_accepts_valid_arxiv_id_shape(self, server, monkeypatch):
        """Sanity: a well-formed id passes the guard and reaches the HTTP layer."""

        class _Resp:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"results": []}

        monkeypatch.setattr(research_server_module.requests, "get", lambda *a, **k: _Resp())
        monkeypatch.setattr(research_server_module, "_arxiv_jitter", _no_sleep)
        results = server.papers_with_code_link("2402.12345")
        assert results == [{"info": "no paper-with-code entry for 2402.12345"}]


# ---------------------------------------------------------------------------
# api.routes.rl: agent_id whitelist must short-circuit BEFORE any FS stat
# ---------------------------------------------------------------------------


def _no_exists(self, *_args, **_kwargs):
    raise AssertionError(f"Path.exists must not be called for a traversal agent_id (got {self!r})")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_agent_id", ["../evil", "a b"])
async def test_get_rl_policy_rejects_invalid_agent_id_before_fs(bad_agent_id):
    """Traversal / spaced agent ids return exists=False without touching disk."""
    with patch("cohezion.api.routes.rl.Path.exists", _no_exists):
        response = await get_rl_policy(bad_agent_id)
    assert isinstance(response, RLPolicyResponse)
    assert response.exists is False
    assert response.checkpoint_path is None


# ---------------------------------------------------------------------------
# substrate.popcorn: kernel whitelist must short-circuit BEFORE subprocess
# ---------------------------------------------------------------------------


def _no_subprocess_run(*_args, **_kwargs):
    raise AssertionError("subprocess.run must not be called for an invalid kernel name")


def test_popcorn_submit_rejects_invalid_kernel_before_subprocess():
    """Injection-shaped kernel name returns an error SubmitResult without exec."""
    with patch("cohezion.substrate.popcorn.subprocess.run", _no_subprocess_run):
        result = popcorn_submit("x; rm -rf /", "submission.py")
    assert isinstance(result, popcorn_module.SubmitResult)
    assert result.passed is False
    assert result.score == 0.0
    assert "Invalid kernel name" in result.error
    assert "x; rm -rf /" in result.error
    assert result.stdout == "" and result.stderr == ""
    assert result.elapsed_s == 0.0
