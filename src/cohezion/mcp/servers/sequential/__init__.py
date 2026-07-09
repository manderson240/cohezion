import contextlib


with contextlib.suppress(Exception):
    from cohezion.mcp.servers.sequential.server import ThinkingSession as ThinkingSession
