import contextlib

with contextlib.suppress(Exception):
    from cohezion.mcp.servers.journey.server import create_app as create_app
