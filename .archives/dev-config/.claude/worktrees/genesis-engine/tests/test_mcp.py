"""Tests for MCP Registry and Servers."""

from cohezion.mcp.registry import MCPRegistry, get_registry


class TestMCPRegistry:
    """Test MCP Registry functionality."""

    def test_registry_loads(self):
        """Registry loads from JSON."""
        registry = get_registry()
        assert registry is not None
        assert isinstance(registry, MCPRegistry)

    def test_list_servers(self):
        """Can list all servers."""
        registry = get_registry()
        servers = registry.list_servers()
        assert len(servers) >= 4  # At least internal servers

    def test_list_tools(self):
        """Can list all tools."""
        registry = get_registry()
        tools = registry.list_tools()
        assert len(tools) >= 12  # 4 servers × 3 tools

    def test_get_server_by_name(self):
        """Can get server by name."""
        registry = get_registry()
        server = registry.get_server("cohezion-knowledge")
        assert server is not None
        assert server.name == "cohezion-knowledge"

    def test_server_has_tools(self):
        """Servers have tools defined."""
        registry = get_registry()
        server = registry.get_server("cohezion-knowledge")
        assert server.tools is not None
        assert "search_knowledge" in server.tools


class TestKnowledgeMCP:
    """Test Knowledge MCP Server."""

    def test_server_loads(self):
        """Knowledge server initializes."""
        from cohezion.mcp.knowledge_server import get_server

        server = get_server()
        assert server is not None

    def test_list_skills(self):
        """Can list skills."""
        from cohezion.mcp.knowledge_server import get_server

        server = get_server()
        skills = server.list_skills()
        assert len(skills) > 0

    def test_search_knowledge(self):
        """Can search knowledge."""
        from cohezion.mcp.knowledge_server import get_server

        server = get_server()
        results = server.search_knowledge("swarm")
        assert len(results) > 0


class TestSkillsMCP:
    """Test Skills MCP Server."""

    def test_server_loads(self):
        """Skills server initializes."""
        from cohezion.mcp.skills_server import get_server

        server = get_server()
        assert server is not None

    def test_list_all(self):
        """Can list all skills."""
        from cohezion.mcp.skills_server import get_server

        server = get_server()
        skills = server.list_all()
        assert isinstance(skills, list)
