import contextlib

with contextlib.suppress(Exception):
    from cohezion.mcp.servers.git.server import GitContext as GitContext
