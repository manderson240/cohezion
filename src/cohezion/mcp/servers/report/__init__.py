import contextlib


with contextlib.suppress(Exception):
    from cohezion.mcp.servers.report.server import MarimoReportGenerator as MarimoReportGenerator
