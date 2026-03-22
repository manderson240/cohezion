from cohezion_branding_mcp import get_ascii_logo, get_brand_colors, get_brand_identity
from rich.console import Console
from rich.panel import Panel


def verify_mcp_interfaces():
    console = Console()
    console.print(Panel("[bold green]Verifying Cohezion Branding MCP...[/bold green]"))

    # 1. Check Colors
    colors = get_brand_colors()
    if colors["nexus_green"] == "#00FF00":
        console.print("✅ Colors: Nexus Green verification [bold green]PASSED[/bold green]")
    else:
        console.print("❌ Colors: Verification [bold red]FAILED[/bold red]")

    # 2. Check Identity
    identity = get_brand_identity()
    if identity["philosophy"] == "Organic Modularity":
        console.print("✅ Identity: Philosophy verification [bold green]PASSED[/bold green]")
    else:
        console.print("❌ Identity: Verification [bold red]FAILED[/bold red]")

    # 3. Check Logo
    logo = get_ascii_logo()
    if "XXX" in logo:
        console.print("✅ Logo: ASCII Motif verification [bold green]PASSED[/bold green]")
        console.print(logo)
    else:
        console.print("❌ Logo: Verification [bold red]FAILED[/bold red]")


if __name__ == "__main__":
    verify_mcp_interfaces()
