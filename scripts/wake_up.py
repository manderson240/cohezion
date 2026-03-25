import sys
from pathlib import Path


# Add src to path just in case
sys.path.append(str(Path(__file__).parent.parent / "src"))



def main():
    print("--------------------------------------------------")
    print("      🌌 COHEZION MCP FLEET WAKE-UP 🌌      ")
    print("--------------------------------------------------")

    dm = get_daemon_manager()
    dm.wake_up()

    print("--------------------------------------------------")
    print("Cohezion services are waking up.")
    print("--------------------------------------------------")


if __name__ == "__main__":
    asyncio.run(main())
