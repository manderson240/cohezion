import contextlib

with contextlib.suppress(Exception):
    from cohezion.mcp.servers.simulate.server import create_app as create_app
