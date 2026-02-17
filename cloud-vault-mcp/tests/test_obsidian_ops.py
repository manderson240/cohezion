"""Tests for Obsidian-aware operations."""

import pytest

from mcp_server.obsidian_ops import ObsidianOps
from mcp_server.vault_ops import VaultOps


@pytest.fixture
def vault_with_links(tmp_path):
    """Create a vault with interlinked notes."""
    for d in ["decisions", "patterns", "projects", "concepts"]:
        (tmp_path / d).mkdir()

    (tmp_path / "decisions" / "_template.md").write_text(
        "---\ndate: {{date}}\nproject: {{project}}\nstatus: accepted\n"
        "tags: [decision, {{project}}]\n---\n# {{title}}\n\n"
        "## Context\n{{context}}\n\n## Decision\n{{decision}}\n\n"
        "## Rationale\n{{rationale}}\n\n## Alternatives Considered\n{{alternatives}}\n"
    )

    (tmp_path / "projects" / "myproject.md").write_text(
        "---\ntags: [project, myproject]\n---\n# My Project\n\nKey decisions:\n- [[use-python]]\n- [[retry-pattern]]\n"
    )
    (tmp_path / "decisions" / "use-python.md").write_text(
        "---\ntags: [decision, myproject]\n---\n# Use Python\n\n"
        "We chose [[Python]] because of [[FastMCP]].\n"
        "Related: [[myproject]]\n"
    )
    (tmp_path / "patterns" / "retry-pattern.md").write_text(
        "---\ntags: [pattern, devops]\n---\n# Retry Pattern\n\nSee [[use-python]] for context.\n#networking\n"
    )
    (tmp_path / "concepts" / "Python.md").write_text(
        "---\ntags: [concept, language]\n---\n# Python\n\nA programming language.\n"
    )

    vault = VaultOps(str(tmp_path))
    return ObsidianOps(vault)


class TestBacklinks:
    def test_find_backlinks(self, vault_with_links):
        results = vault_with_links.backlinks("decisions/use-python.md")
        sources = [r["source"] for r in results]
        assert "projects/myproject.md" in sources
        assert "patterns/retry-pattern.md" in sources

    def test_no_backlinks(self, vault_with_links):
        results = vault_with_links.backlinks("patterns/retry-pattern.md")
        sources = [r["source"] for r in results]
        assert "projects/myproject.md" in sources


class TestForwardLinks:
    def test_find_forward_links(self, vault_with_links):
        results = vault_with_links.forward_links("decisions/use-python.md")
        links = [r["link"] for r in results]
        assert "Python" in links
        assert "FastMCP" in links
        assert "myproject" in links

    def test_existing_links_resolved(self, vault_with_links):
        results = vault_with_links.forward_links("decisions/use-python.md")
        python_link = next(r for r in results if r["link"] == "Python")
        assert python_link["exists"] is True
        assert python_link["resolved_path"] == "concepts/Python.md"


class TestTags:
    def test_tags_for_note(self, vault_with_links):
        tags = vault_with_links.tags("patterns/retry-pattern.md")
        assert "pattern" in tags
        assert "devops" in tags
        assert "networking" in tags

    def test_all_tags(self, vault_with_links):
        tags = vault_with_links.tags()
        assert "decision" in tags
        assert "pattern" in tags
        assert "project" in tags
        assert "networking" in tags


class TestCreateFromTemplate:
    def test_create_from_template(self, vault_with_links):
        result = vault_with_links.create_from_template(
            "decisions",
            "decisions/new-decision.md",
            {
                "project": "testproj",
                "title": "Use Docker",
                "context": "Need containerization",
                "decision": "Use Docker Compose",
                "rationale": "Simple orchestration",
                "alternatives": "Kubernetes (overkill)",
            },
        )
        assert "Created" in result

        content = vault_with_links.vault.read("decisions/new-decision.md")
        assert "Use Docker" in content
        assert "testproj" in content
        assert "Simple orchestration" in content

    def test_template_not_found(self, vault_with_links):
        with pytest.raises(FileNotFoundError):
            vault_with_links.create_from_template("nonexistent", "test.md", {})
