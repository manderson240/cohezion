import contextlib


with contextlib.suppress(Exception):
    from cohezion.mcp.servers.github.server import GitHubService as GitHubService
