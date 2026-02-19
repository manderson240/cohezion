"""Verification script for Agentic Journey Perception in the Quadrature Nexus."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from cohezion.swarm import QuadratureNexus
from cohezion.swarm.topology import NodeRole
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def verify_perception():
    print("\n--- [VERIFICATION] Agentic Journey Perception ---\n")
    print("[DEBUG] Path: ", sys.path)
    
    with patch("cohezion.swarm.executive.get_mcp_client") as mock_mcp:
        mock_mcp.return_value = MagicMock()
        print("[DEBUG] MCP client mocked.")
        
        print("[DEBUG] Initializing Nexus...")
        # 1. Initialize Nexus
        nexus = QuadratureNexus(mission_id="verification_nexus_01")
        print("[DEBUG] Nexus initialized.")
    
    # 2. Fabric Initialization (Records Events)
    print("Initializing Fabrics...")
    nexus.create_fabric_swarm("space", NodeRole.ARCHITECT)
    nexus.create_fabric_swarm("field", NodeRole.ENGINEER)
    nexus.create_fabric_swarm("control", NodeRole.QUANTUM_ALGO)
    nexus.create_fabric_swarm("precipitation", NodeRole.BIOLOGIST)
    
    # 3. Execute Mission (Records Intent + Outcome)
    print("\nExecuting Mission: 'Ascend to Horizon Alpha'...")
    await nexus.execute_mission("Ascend to Horizon Alpha")
    
    # 4. Generate Showreel
    print("\nGenerating Showreel Report...")
    showreel = nexus.generate_journey_report()
    
    print("\n--- SHOWREEL OUTPUT ---\n")
    print(showreel)
    print("\n--- END SHOWREEL ---\n")

if __name__ == "__main__":
    asyncio.run(verify_perception())
