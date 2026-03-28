import asyncio
import sys
from pathlib import Path


# Add src to path just in case
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cohezion.mcp.manager.server_manager import get_manager, init_default_servers


async def main():
    print("--------------------------------------------------")
    print("      🌌 COHEZION MCP FLEET WAKE-UP 🌌      ")
    print("--------------------------------------------------")

    init_default_servers()
    manager = get_manager()

    print(f"Starting {len(manager.servers)} MCP servers...")
    await manager.start_all()

    status = manager.get_status()
    print(f"Manager running on port {status['manager']['port']}")
    for name, config in status["servers"].items():
        print(f"  [ {config['status'].upper():8} ] {name:15} on port {config['port']}")

    print("--------------------------------------------------")
    print("🚀 Waking up Living Research Substrate (Marimo)...")
    try:
        import subprocess

        marimo_script = Path(__file__).parent / "start_marimo.sh"
        _ = subprocess.Popen(
            [str(marimo_script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print("  [ RUNNING  ] marimo server on port 8081")
    except Exception as e:
        print(f"  [ ERROR    ] Failed to start marimo: {e}")

    print("--------------------------------------------------")
    print("Cohezion services are waking up.")
    print("--------------------------------------------------")


if __name__ == "__main__":
    asyncio.run(main())
