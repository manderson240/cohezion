"""Tests for agent file validation schema."""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.validation.agent_schema import (
    AgentFileSchema,
    AgentFileValidationError,
    extract_frontmatter,
    generate_agent_frontmatter,
    validate_agent_file,
    validate_all_agent_files,
)


class TestExtractFrontmatter:
    """Test YAML frontmatter extraction."""

    def test_valid_frontmatter(self):
        text = "---\nname: test\ndescription: A test agent\n---\n# Body"
        result = extract_frontmatter(text)
        assert result == {"name": "test", "description": "A test agent"}

    def test_missing_frontmatter(self):
        text = "# Just a markdown file\nNo frontmatter here."
        result = extract_frontmatter(text)
        assert result == {}

    def test_empty_frontmatter(self):
        text = "---\n---\n# Body"
        result = extract_frontmatter(text)
        assert result == {}

    def test_non_dict_frontmatter(self):
        text = "---\n- item1\n- item2\n---\n# Body"
        result = extract_frontmatter(text)
        assert result == {}

    def test_frontmatter_with_lists(self):
        text = "---\nname: test\ndescription: A test agent for things\ntools:\n  - Read\n  - Glob\n---\n"
        result = extract_frontmatter(text)
        assert result["tools"] == ["Read", "Glob"]


class TestAgentFileSchema:
    """Test Pydantic schema validation."""

    def test_valid_minimal(self):
        schema = AgentFileSchema(name="my-agent", description="A minimal test agent")
        assert schema.name == "my-agent"
        assert schema.tools is None

    def test_valid_full(self):
        schema = AgentFileSchema(
            name="test-runner",
            description="Runs pytest suites and reports coverage",
            tools=["Bash", "Read"],
            disallowedTools=["Edit", "Write"],
            model="sonnet",
        )
        assert schema.name == "test-runner"
        assert schema.tools == ["Bash", "Read"]
        assert schema.disallowedTools == ["Edit", "Write"]
        assert schema.model == "sonnet"

    def test_missing_name(self):
        with pytest.raises((ValueError, RuntimeError, TypeError)):  # ValidationError
            AgentFileSchema(description="A valid description here")

    def test_missing_description(self):
        with pytest.raises((ValueError, RuntimeError, TypeError)):  # ValidationError
            AgentFileSchema(name="my-agent")

    def test_invalid_name_uppercase(self):
        with pytest.raises((ValueError, RuntimeError, TypeError)):
            AgentFileSchema(name="MyAgent", description="Has uppercase letters")

    def test_invalid_name_spaces(self):
        with pytest.raises((ValueError, RuntimeError, TypeError)):
            AgentFileSchema(name="my agent", description="Has spaces in name")

    def test_invalid_name_starts_with_number(self):
        with pytest.raises((ValueError, RuntimeError, TypeError)):
            AgentFileSchema(name="1agent", description="Starts with number")

    def test_description_too_short(self):
        with pytest.raises((ValueError, RuntimeError, TypeError)):
            AgentFileSchema(name="my-agent", description="Short")

    def test_extra_fields_rejected(self):
        with pytest.raises((ValueError, RuntimeError, TypeError)):
            AgentFileSchema(
                name="my-agent",
                description="A valid description here",
                unknownField="should fail",
            )


class TestGenerateAgentFrontmatter:
    """Test frontmatter generation."""

    def test_minimal(self):
        result = generate_agent_frontmatter(
            name="my-agent",
            description="A minimal test agent",
        )
        assert "---" in result
        assert "name: my-agent" in result
        assert "description: A minimal test agent" in result

    def test_full(self):
        result = generate_agent_frontmatter(
            name="my-agent",
            description="A full test agent with all options",
            tools=["Read", "Glob"],
            disallowed_tools=["Bash"],
            model="sonnet",
        )
        assert "tools:" in result
        assert "- Read" in result
        assert "disallowedTools:" in result
        assert "model: sonnet" in result

    def test_invalid_name_raises(self):
        with pytest.raises((AgentFileValidationError, Exception)):
            generate_agent_frontmatter(
                name="INVALID",
                description="Has uppercase name",
            )

    def test_roundtrip(self):
        """Generated frontmatter should parse back to the same schema."""
        original = generate_agent_frontmatter(
            name="roundtrip-test",
            description="Testing the roundtrip parse capability",
            tools=["Read", "Bash"],
            model="haiku",
        )
        parsed = extract_frontmatter(original)
        schema = AgentFileSchema(**parsed)
        assert schema.name == "roundtrip-test"
        assert schema.tools == ["Read", "Bash"]
        assert schema.model == "haiku"


class TestValidateExistingAgentFiles:
    """Integration: validate real agent files in the repository."""

    def test_all_agent_files_valid(self):
        """All existing .claude/agents/*.md files must pass validation."""
        results = validate_all_agent_files()
        assert len(results) >= 3  # At least our 3 known agents
        names = {r.name for r in results}
        assert "test-runner" in names
        assert "code-reviewer" in names
        assert "simulation-runner" in names

    def test_validate_single_file(self):
        """Validate a single known agent file."""
        import shutil
        import subprocess

        git_cmd = shutil.which("git") or "git"
        root = subprocess.run(
            [git_cmd, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            shell=False,
        ).stdout.strip()
        path = Path(root) / ".claude" / "agents" / "test-runner.md"
        result = validate_agent_file(path)
        assert result.name == "test-runner"
        assert result.model == "sonnet"

    def test_invalid_file_raises(self, tmp_path):
        """A file with bad frontmatter should raise AgentFileValidationError."""
        bad_file = tmp_path / "bad-agent.md"
        bad_file.write_text("---\nname: INVALID\n---\n# Bad")
        with pytest.raises(AgentFileValidationError):
            validate_agent_file(bad_file)
