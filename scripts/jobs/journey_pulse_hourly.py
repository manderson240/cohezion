#!/usr/bin/env python3
"""
Hourly Job: Journey Dashboard Pulse
Showcases SKILL: JOURNEY_DASHBOARD_PRIME
Delegate: phi4-mini (Efficiency)
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from cohezion.swarm.compound_client import get_compound_client


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("JourneyPulse")


async def main():
    logger.info("🌌 Starting Hourly Journey Pulse...")

    # 1. Sense: Read recent trajectories with Physics-Grounded parameters (L133, L146)
    # Mapping 8 Brane dimensions to Vacuum Engineering / Propulsion states.
    mock_trajectory = {
        "journey_id": "journey_plasma_42",
        "step": 108,
        "coherence": 0.50,  # HIHO Stability Target
        "phi_score": 0.92,
        "alfven_velocity": 0.85,  # L133: Energy transfer velocity
        "brane_thrust_mN": 35.2,  # L146: CID Propellant-free force
        "state_vector": [
            0.5,
            0.5,
            0.5,
            0.5,  # Spatial + Time
            0.1,
            0.9,
            0.4,
            0.2,  # Brane 1-4 (Propulsion)
            0.8,
            0.3,
            0.6,
            0.5,  # Brane 5-8 (Stability)
        ],
    }

    # 2. Distill: Delegate to phi4-mini with Research Context
    client = get_compound_client()
    prompt = f"""
    You are a JOURNEY_DASHBOARD_PRIME specialist. 
    Map this 12D physics trajectory (Alfven-waves, CID Thrust) to our dashboard.
    
    Data: {json.dumps(mock_trajectory)}
    
    Instruction:
    - Use 'alfven_velocity' to set the pulse frequency.
    - Map 'brane_thrust_mN' to the particle emission rate.
    - Ensure the 'coherence' 0.5 attractor is visually highlighted.
    """

    # Force use of phi4-mini via task_type mapping if possible,
    # or just use standard generation which the router will handle.
    response, tokens = await client.generate(prompt, task_type="telemetry")

    # 3. Manifest: Save to dashboard assets
    output_dir = Path("apps/dashboard/src/assets/data")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H")
    output_file = output_dir / f"pulse_{timestamp}.json"

    with open(output_file, "w") as f:
        f.write(response)

    logger.info(f"✅ Journey Pulse manifest created: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
