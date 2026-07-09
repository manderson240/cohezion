import contextlib


with contextlib.suppress(Exception):
    from cohezion.mcp.servers.huggingface.server import HuggingFaceService as HuggingFaceService
