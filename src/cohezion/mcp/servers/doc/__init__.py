import contextlib

with contextlib.suppress(Exception):
    from cohezion.mcp.servers.doc.server import create_app as create_app
