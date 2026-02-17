"""Tool handler implementations for Cohezion MCP Server."""

from cohezion.skills.mcp_handlers_config import ConfigHandlers
from cohezion.skills.mcp_handlers_elite import EliteHandlers
from cohezion.skills.mcp_handlers_util import UtilHandlers


class ToolHandlersMixin(EliteHandlers, UtilHandlers, ConfigHandlers):
    """Combined mixin providing all tool handler methods."""

    pass
