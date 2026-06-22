import contextlib

with contextlib.suppress(Exception):
    from cohezion.mcp.servers.security.server import SecurityScanner as SecurityScanner
