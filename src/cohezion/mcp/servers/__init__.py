import contextlib

with contextlib.suppress(Exception):
    from cohezion.mcp.servers.safe_input import sanitize_path as sanitize_path

with contextlib.suppress(Exception):
    from cohezion.mcp.servers.safe_input import sanitize_log as sanitize_log
