
import sys
import os
from pathlib import Path

# Add src to path just in case
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cohezion.system.daemon_manager import get_daemon_manager

def main():
    print("--------------------------------------------------")
    print("      🌌 COHEZION AUTONOMOUS BOOTSTRAP 🌌      ")
    print("--------------------------------------------------")
    
    dm = get_daemon_manager()
    dm.wake_up()
    
    print("--------------------------------------------------")
    print("Run '/audit' for health check or check the HUD.")
    print("--------------------------------------------------")

if __name__ == "__main__":
    main()
