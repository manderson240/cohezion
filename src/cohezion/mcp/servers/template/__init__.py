import contextlib


with contextlib.suppress(Exception):
    from cohezion.mcp.servers.template.server import WeatherService as WeatherService
