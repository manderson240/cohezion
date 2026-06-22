import contextlib

with contextlib.suppress(Exception):
    from cohezion.mcp.servers.rewards.server import app as app
