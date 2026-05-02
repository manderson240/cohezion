from mcp.server.fastmcp import FastMCP

from cohezion.branding import Colors, Identity, Motifs


mcp = FastMCP("cohezion-branding")


@mcp.tool()
def get_brand_colors() -> dict:
    """Returns the official Cohezion color palette."""
    return {
        "nexus_green": Colors.NEXUS_GREEN,
        "matte_black": Colors.MATTE_BLACK,
        "silicon_silver": Colors.SILICON_SILVER,
        "earth_blue": Colors.EARTH_BLUE,
        "critical_red": Colors.CRITICAL_RED,
        "warning_gold": Colors.WARNING_GOLD,
    }


@mcp.tool()
def get_brand_identity() -> dict:
    """Returns the Cohezion identity and philosophy."""
    return {
        "name": Identity.NAME,
        "tagline": Identity.TAGLINE,
        "philosophy": Identity.PHILOSOPHY,
    }


@mcp.tool()
def get_ascii_logo() -> str:
    """Returns the official Cohezion ASCII logo."""
    return Motifs.NEXUS_LOGO


if __name__ == "__main__":
    mcp.run()
