"""Tests for mcp_server/graph_writer.py."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from mcp_server.graph_writer import (
    annotate_neuron,
    batch_upsert_neurons,
    compute_activation,
    compute_stage,
    create_synapse,
    escape_sql,
    escape_tag_list,
    slugify,
    upsert_neuron,
    validate_surreal_id,
)


# ── Helper function tests (pure logic, no mocking) ──────────────────────────


class TestSlugify:
    """Tests for slugify helper."""

    def test_basic_conversion_p0(self):
        """[P0] Converts text to valid SurrealDB ID component."""
        assert slugify("Agent Architecture") == "agent_architecture"

    def test_special_characters_p1(self):
        """[P1] Strips special characters and normalizes whitespace."""
        assert slugify("hello-world (v2.0)") == "hello_world_v20"

    def test_strips_leading_trailing_underscores_p2(self):
        """[P2] Strips leading/trailing underscores from result."""
        assert slugify("  test  ") == "test"


class TestComputeStage:
    """Tests for compute_stage helper."""

    def test_embryo_p0(self):
        """[P0] Word count < 100 returns embryo."""
        assert compute_stage(50) == "embryo"

    def test_growing_p0(self):
        """[P0] Word count 100-399 returns growing."""
        assert compute_stage(200) == "growing"

    def test_mature_p0(self):
        """[P0] Word count >= 400 returns mature."""
        assert compute_stage(500) == "mature"


class TestComputeActivation:
    """Tests for compute_activation helper."""

    def test_returns_float_in_range_p0(self):
        """[P0] Activation is a float between 0 and 1."""
        result = compute_activation(200, "growing", ["tag1", "tag2"])
        assert 0.0 <= result <= 1.0

    def test_mature_higher_than_embryo_p1(self):
        """[P1] Mature notes have higher activation than embryo notes."""
        embryo = compute_activation(50, "embryo", [])
        mature = compute_activation(500, "mature", ["a", "b", "c", "d"])
        assert mature > embryo

    def test_recency_boost_p1(self):
        """[P1] Recent creation date boosts activation."""
        from datetime import date

        today = date.today().isoformat()
        with_recency = compute_activation(200, "growing", ["tag"], today)
        without_recency = compute_activation(200, "growing", ["tag"], "")
        assert with_recency > without_recency


class TestEscapeSql:
    """Tests for escape_sql helper."""

    def test_escapes_single_quotes_p0(self):
        """[P0] Single quotes are escaped for SurrealQL."""
        assert "\\'" in escape_sql("it's a test")

    def test_truncates_at_2000_p1(self):
        """[P1] Output is truncated to 2000 characters."""
        long_text = "a" * 3000
        assert len(escape_sql(long_text)) <= 2000


# ── Async function tests (mock httpx) ───────────────────────────────────────


def _make_ok_response():
    """Create a mock httpx response that returns OK status."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = [{"status": "OK", "result": []}]
    return mock_resp


@pytest.mark.asyncio
async def test_upsert_neuron_success_p0():
    """[P0] upsert_neuron returns True on successful HTTP response."""
    mock_resp = _make_ok_response()
    with patch("httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__ = AsyncMock(
            return_value=MagicMock(post=AsyncMock(return_value=mock_resp))
        )
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await upsert_neuron(
            neuron_id="neuron:test_md",
            title="Test",
            cluster="cortex",
            content="some content here for word count",
        )
        assert result is True


@pytest.mark.asyncio
async def test_upsert_neuron_failure_returns_false_p1():
    """[P1] upsert_neuron returns False when HTTP call raises."""
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("connection refused")
        )
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await upsert_neuron(
            neuron_id="neuron:test_md",
            title="Test",
        )
        assert result is False


@pytest.mark.asyncio
async def test_create_synapse_maps_nonstandard_type_p1():
    """[P1] create_synapse maps non-schema link_type to latent with reason prefix."""
    mock_resp = _make_ok_response()
    captured_sql = []

    async def capture_post(url, **kwargs):
        captured_sql.append(kwargs.get("content", ""))
        return mock_resp

    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=capture_post)

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        await create_synapse(
            from_id="neuron:a",
            to_id="neuron:b",
            link_type="k-search-child",
            reason="test reason",
        )

    assert len(captured_sql) == 1
    sql = captured_sql[0]
    assert "'latent'" in sql  # mapped from k-search-child
    assert "[k-search-child]" in sql  # original type preserved in reason


# ── Security validation tests ─────────────────────────────────────────────


class TestValidateSurrealId:
    """Tests for validate_surreal_id (SQL injection prevention)."""

    def test_valid_neuron_id_p0(self):
        """[P0] Accepts well-formed neuron IDs."""
        assert validate_surreal_id("neuron:test_md") == "neuron:test_md"

    def test_valid_id_with_hyphens_and_dots_p0(self):
        """[P0] Accepts IDs containing hyphens and dots."""
        assert validate_surreal_id("neuron:my-note.v2") == "neuron:my-note.v2"

    def test_rejects_semicolon_injection_p0(self):
        """[P0] Rejects IDs containing semicolons (SQL injection vector)."""
        with pytest.raises(ValueError, match="Invalid SurrealDB identifier"):
            validate_surreal_id("neuron:x; DELETE neuron;--")

    def test_rejects_single_quote_injection_p0(self):
        """[P0] Rejects IDs with single quotes."""
        with pytest.raises(ValueError, match="Invalid SurrealDB identifier"):
            validate_surreal_id("neuron:x' OR '1'='1")

    def test_rejects_space_injection_p1(self):
        """[P1] Rejects IDs containing spaces."""
        with pytest.raises(ValueError, match="Invalid SurrealDB identifier"):
            validate_surreal_id("neuron:x SET admin = true")

    def test_rejects_empty_string_p1(self):
        """[P1] Rejects empty identifier."""
        with pytest.raises(ValueError, match="Invalid SurrealDB identifier"):
            validate_surreal_id("")

    def test_rejects_numeric_start_p2(self):
        """[P2] Rejects identifiers starting with a digit."""
        with pytest.raises(ValueError, match="Invalid SurrealDB identifier"):
            validate_surreal_id("123neuron")


class TestEscapeTagList:
    """Tests for escape_tag_list (tag array SQL injection prevention)."""

    def test_basic_tags_p0(self):
        """[P0] Produces valid SurrealQL array of escaped strings."""
        result = escape_tag_list(["alpha", "beta"])
        assert result == "['alpha', 'beta']"

    def test_empty_list_p0(self):
        """[P0] Empty list produces empty SurrealQL array."""
        assert escape_tag_list([]) == "[]"

    def test_escapes_quotes_in_tags_p0(self):
        """[P0] Tags with single quotes are escaped."""
        result = escape_tag_list(["it's", "test"])
        assert "\\'" in result
        assert result.startswith("[")
        assert result.endswith("]")

    def test_injection_via_tag_p0(self):
        """[P0] SQL injection payload in tag is neutralized."""
        result = escape_tag_list(["'); DELETE neuron; --"])
        # The quote is escaped with backslash, so the SQL cannot break out
        assert "\\'" in result
        # Verify that every single quote in the output is either the
        # outermost delimiters or preceded by a backslash (escaped)
        inner = result[1:-1]  # strip [ and ]
        # The escaped result should be: '\'); DELETE neuron; --'
        # The inner single quotes are the delimiters; the ) quote is escaped
        assert inner.startswith("'") and inner.endswith("'")
        content = inner[1:-1]  # strip delimiter quotes
        # Inside the delimiters, all quotes must be escaped
        assert "'" not in content.replace("\\'", "")


# ── annotate_neuron tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_annotate_neuron_success_p0():
    """[P0] annotate_neuron returns True on successful HTTP response."""
    mock_resp = _make_ok_response()
    with patch("httpx.AsyncClient") as MockClient:
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await annotate_neuron(neuron_id="neuron:test_md")
        assert result is True


@pytest.mark.asyncio
async def test_annotate_neuron_only_updates_timestamps_p0():
    """[P0] annotate_neuron SQL only sets last_fired and modified (schemaful constraint)."""
    mock_resp = _make_ok_response()
    captured_sql = []

    async def capture_post(url, **kwargs):
        captured_sql.append(kwargs.get("content", ""))
        return mock_resp

    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=capture_post)

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        await annotate_neuron(neuron_id="neuron:test_md", agent_notes="some notes")

    assert len(captured_sql) == 1
    sql = captured_sql[0]
    assert "last_fired" in sql
    assert "modified" in sql
    # Schemaful constraint: must NOT set agent_notes or access_count
    assert "agent_notes" not in sql
    assert "access_count" not in sql


@pytest.mark.asyncio
async def test_annotate_neuron_rejects_bad_id_p0():
    """[P0] annotate_neuron raises ValueError on malicious neuron_id."""
    with pytest.raises(ValueError, match="Invalid SurrealDB identifier"):
        await annotate_neuron(neuron_id="neuron:x; DROP TABLE neuron;--")


@pytest.mark.asyncio
async def test_annotate_neuron_failure_returns_false_p1():
    """[P1] annotate_neuron returns False when HTTP call raises."""
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("connection refused")
        )
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await annotate_neuron(neuron_id="neuron:test_md")
        assert result is False


# ── batch_upsert_neurons tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_upsert_neurons_success_p0():
    """[P0] batch_upsert_neurons returns count of successful upserts."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = [
        {"status": "OK", "result": []},
        {"status": "OK", "result": []},
    ]

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        neurons = [
            {"neuron_id": "neuron:a", "title": "Alpha", "tags": ["t1"]},
            {"neuron_id": "neuron:b", "title": "Beta", "content": "some words"},
        ]
        count = await batch_upsert_neurons(neurons)
        assert count == 2


@pytest.mark.asyncio
async def test_batch_upsert_joins_statements_p0():
    """[P0] batch_upsert_neurons joins multiple UPSERT statements into one SQL payload."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = [
        {"status": "OK", "result": []},
        {"status": "OK", "result": []},
        {"status": "OK", "result": []},
    ]
    captured_sql = []

    async def capture_post(url, **kwargs):
        captured_sql.append(kwargs.get("content", ""))
        return mock_resp

    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=capture_post)

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        neurons = [
            {"neuron_id": "neuron:a", "title": "Alpha"},
            {"neuron_id": "neuron:b", "title": "Beta"},
            {"neuron_id": "neuron:c", "title": "Gamma"},
        ]
        await batch_upsert_neurons(neurons)

    # Single HTTP call with all statements joined
    assert len(captured_sql) == 1
    sql = captured_sql[0]
    assert sql.count("UPSERT neuron:") == 3
    assert "neuron:a" in sql
    assert "neuron:b" in sql
    assert "neuron:c" in sql


@pytest.mark.asyncio
async def test_batch_upsert_empty_list_p1():
    """[P1] batch_upsert_neurons returns 0 for empty input."""
    count = await batch_upsert_neurons([])
    assert count == 0


@pytest.mark.asyncio
async def test_batch_upsert_rejects_bad_id_p0():
    """[P0] batch_upsert_neurons raises ValueError on malicious neuron_id."""
    neurons = [{"neuron_id": "neuron:ok", "title": "OK"},
               {"neuron_id": "bad; DROP TABLE", "title": "Evil"}]
    with pytest.raises(ValueError, match="Invalid SurrealDB identifier"):
        await batch_upsert_neurons(neurons)
