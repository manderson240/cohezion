"""vault_graph — typed wrappers around the SurrealDB graph intelligence layer."""

from .client import GraphClient, GraphQueryError, get_graph_client
from . import queries

__all__ = ["GraphClient", "GraphQueryError", "get_graph_client", "queries"]
