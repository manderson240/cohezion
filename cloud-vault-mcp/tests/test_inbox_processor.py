"""Tests for inbox processor: classify, expand, and file notes."""

import json
from unittest.mock import MagicMock

import pytest

from mcp_server.inbox_processor import (
    Classification,
    InboxProcessor,
)
from mcp_server.vault_ops import VaultOps


def _make_classification(
    note_type="research",
    title="Test Note",
    target_dir="papers/",
    task="expand_research",
    summary="A test note",
):
    return {
        "note_type": note_type,
        "title": title,
        "target_dir": target_dir,
        "task": task,
        "summary": summary,
    }


def _make_mock_anthropic(classify_response, execute_response=None):
    """Create a mock anthropic.Anthropic client."""
    client = MagicMock()
    call_count = [0]

    def create_message(**kwargs):
        call_count[0] += 1
        mock_response = MagicMock()
        if call_count[0] == 1:
            mock_response.content = [MagicMock(text=json.dumps(classify_response))]
        else:
            mock_response.content = [
                MagicMock(text=execute_response or "Processed content")
            ]
        return mock_response

    client.messages.create = create_message
    return client


@pytest.fixture
def vault(tmp_path):
    """Create a vault with an inbox directory."""
    (tmp_path / "inbox").mkdir()
    (tmp_path / "papers").mkdir()
    (tmp_path / "decisions").mkdir()
    (tmp_path / "experiments").mkdir()
    (tmp_path / "patterns").mkdir()
    (tmp_path / "concepts").mkdir()
    (tmp_path / "projects").mkdir()
    (tmp_path / "daily").mkdir()
    return VaultOps(str(tmp_path))


@pytest.fixture
def compound(vault):
    """Create a stub compound ops (unused by most tests)."""
    return MagicMock()


def _make_processor(vault, compound, classify_resp, execute_resp=None):
    client = _make_mock_anthropic(classify_resp, execute_resp)
    return InboxProcessor(vault, compound, client)


# --- Classification tests ---


class TestClassify:
    async def test_classify_research(self, vault, compound):
        resp = _make_classification(
            "research",
            "Attention Mechanisms",
            "papers/",
            "expand_research",
            "Research on attention",
        )
        processor = _make_processor(vault, compound, resp)

        vault.write(
            "inbox/note.md", "Some notes about attention mechanisms in transformers"
        )
        result = await processor._classify("Some notes about attention mechanisms")

        assert result.note_type == "research"
        assert result.title == "Attention Mechanisms"
        assert result.target_dir == "papers/"
        assert result.task == "expand_research"

    async def test_classify_decision(self, vault, compound):
        resp = _make_classification(
            "decision",
            "Use PostgreSQL",
            "decisions/",
            "structure_decision",
            "Decided to use PG",
        )
        processor = _make_processor(vault, compound, resp)

        result = await processor._classify(
            "We decided to use PostgreSQL for persistence"
        )
        assert result.note_type == "decision"
        assert result.task == "structure_decision"

    async def test_classify_experiment(self, vault, compound):
        resp = _make_classification(
            "experiment",
            "Test Caching",
            "experiments/",
            "structure_experiment",
            "Cache hit test",
        )
        processor = _make_processor(vault, compound, resp)

        result = await processor._classify("What if we add a cache layer?")
        assert result.note_type == "experiment"
        assert result.task == "structure_experiment"

    async def test_classify_pattern(self, vault, compound):
        resp = _make_classification(
            "pattern",
            "Retry with Backoff",
            "patterns/",
            "extract_pattern",
            "Retry pattern",
        )
        processor = _make_processor(vault, compound, resp)

        result = await processor._classify("pattern: retry with exponential backoff")
        assert result.note_type == "pattern"
        assert result.task == "extract_pattern"

    async def test_classify_daily(self, vault, compound):
        resp = _make_classification(
            "daily", "Feb 7 Log", "daily/", "structure_daily", "Daily standup"
        )
        processor = _make_processor(vault, compound, resp)

        result = await processor._classify("Today I worked on the inbox processor")
        assert result.note_type == "daily"
        assert result.task == "structure_daily"

    async def test_classify_concept(self, vault, compound):
        resp = _make_classification(
            "concept",
            "FLUME Manifold",
            "concepts/",
            "define_concept",
            "FLUME definition",
        )
        processor = _make_processor(vault, compound, resp)

        result = await processor._classify("What is a FLUME manifold?")
        assert result.note_type == "concept"
        assert result.task == "define_concept"

    async def test_classify_handles_code_block_wrapper(self, vault, compound):
        """Claude sometimes wraps JSON in markdown code blocks."""
        client = MagicMock()
        wrapped = (
            '```json\n{"note_type":"research","title":"Test",'
            '"target_dir":"papers/","task":"expand_research",'
            '"summary":"test"}\n```'
        )
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=wrapped)]
        client.messages.create = MagicMock(return_value=mock_response)

        processor = InboxProcessor(vault, compound, client)
        result = await processor._classify("some content")
        assert result.note_type == "research"


# --- Full pipeline tests ---


class TestProcessNote:
    async def test_full_pipeline(self, vault, compound):
        classify_resp = _make_classification(
            "decision",
            "Use Redis",
            "decisions/",
            "structure_decision",
            "Redis caching decision",
        )
        processor = _make_processor(
            vault,
            compound,
            classify_resp,
            "# Use Redis\n\n## Context\nNeed fast caching.",
        )

        vault.write("inbox/redis-note.md", "We should use Redis for caching because...")

        result = await processor.process_note("inbox/redis-note.md")

        assert result.success is True
        assert result.source == "inbox/redis-note.md"
        assert result.target.startswith("decisions/")
        assert "use-redis" in result.target
        assert result.classification.note_type == "decision"

        # Verify file was created in target
        content = vault.read(result.target)
        assert "Use Redis" in content

        # Verify inbox file was removed
        with pytest.raises(FileNotFoundError):
            vault.read("inbox/redis-note.md")

    async def test_empty_content(self, vault, compound):
        classify_resp = _make_classification()
        processor = _make_processor(vault, compound, classify_resp)

        vault.write("inbox/empty.md", "   \n  \n  ")

        result = await processor.process_note("inbox/empty.md")

        assert result.success is False
        assert result.error == "Empty note"
        # File should still exist (not deleted on failure)
        assert vault.read("inbox/empty.md") == "   \n  \n  "

    async def test_file_not_found(self, vault, compound):
        classify_resp = _make_classification()
        processor = _make_processor(vault, compound, classify_resp)

        result = await processor.process_note("inbox/nonexistent.md")

        assert result.success is False
        assert "File not found" in result.error

    async def test_classification_failure(self, vault, compound):
        client = MagicMock()
        client.messages.create = MagicMock(side_effect=RuntimeError("API down"))
        processor = InboxProcessor(vault, compound, client)

        vault.write("inbox/broken.md", "Some valid content here")

        result = await processor.process_note("inbox/broken.md")

        assert result.success is False
        assert "Classification failed" in result.error
        # File should still exist
        assert vault.read("inbox/broken.md") == "Some valid content here"

    async def test_task_execution_failure(self, vault, compound):
        """First call (classify) succeeds, second call (execute) fails."""
        client = MagicMock()
        call_count = [0]

        def create_message(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                resp = MagicMock()
                resp.content = [MagicMock(text=json.dumps(_make_classification()))]
                return resp
            raise RuntimeError("Task execution error")

        client.messages.create = create_message
        processor = InboxProcessor(vault, compound, client)

        vault.write("inbox/fail-exec.md", "Content that classifies fine")

        result = await processor.process_note("inbox/fail-exec.md")

        assert result.success is False
        assert "Task execution failed" in result.error
        assert result.classification.note_type == "research"


# --- should_process tests ---


class TestShouldProcess:
    def test_inbox_markdown(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        assert processor.should_process("inbox/my-note.md") is True

    def test_inbox_subdirectory(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        assert processor.should_process("inbox/sub/note.md") is True

    def test_non_inbox_path(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        assert processor.should_process("decisions/some-decision.md") is False

    def test_non_markdown(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        assert processor.should_process("inbox/image.png") is False

    def test_template_file(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        assert processor.should_process("inbox/_template.md") is False

    def test_dotfile(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        assert processor.should_process("inbox/.hidden/note.md") is False

    def test_root_level(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        assert processor.should_process("note.md") is False


# --- Frontmatter tests ---


class TestFrontmatter:
    def test_adds_frontmatter(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        classification = Classification(
            "research", "Test", "papers/", "expand_research", "A summary"
        )

        result = processor._add_frontmatter(
            "# My Content\n\nBody text.", classification, "2026-02-07"
        )

        assert result.startswith("---\n")
        assert "type: research" in result
        assert "source: inbox" in result
        assert "tags: [research, auto-processed]" in result
        assert "summary: A summary" in result
        assert "# My Content" in result

    def test_no_double_frontmatter(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        classification = Classification(
            "research", "Test", "papers/", "expand_research", "A summary"
        )

        content_with_fm = (
            "---\ndate: 2026-02-07\ntype: research\n---\n# Already has frontmatter"
        )
        result = processor._add_frontmatter(
            content_with_fm, classification, "2026-02-07"
        )

        assert result == content_with_fm
        # Should not have double ---
        assert result.count("---") == 2


# --- Slugify tests ---


class TestSlugify:
    def test_basic(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        assert processor._slugify("Hello World") == "hello-world"

    def test_special_characters(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        assert (
            processor._slugify("Use Redis!!! For $caching$") == "use-redis-for-caching"
        )

    def test_truncation(self, vault, compound):
        processor = _make_processor(vault, compound, _make_classification())
        long_title = "A" * 100
        result = processor._slugify(long_title)
        assert len(result) <= 80
