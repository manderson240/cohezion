import contextlib


with contextlib.suppress(Exception):
    from cohezion.mcp.servers.memory.server import MemoryGraph as MemoryGraph
