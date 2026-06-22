import contextlib

with contextlib.suppress(Exception):
    from cohezion.mcp.servers.stitch.client import StitchMCPClient as StitchMCPClient
