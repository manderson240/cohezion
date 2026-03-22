#!/usr/bin/env python3
"""
Universe Precipitation Driver 🌌 (WebSocket Enabled)
===================================================
Executes high-fidelity agentic journeys through the Fractal Manifold,
captures them in SurrealDB 3.0, and broadcasts telemetry over WebSockets.

Displays:
1. Real-time CLI "Minority Report" dashboard.
2. WebSocket stream for the Morphospace Loom React App.
"""

import asyncio
import importlib.util
import json
import logging
import sys
import unittest.mock
from datetime import datetime
from pathlib import Path


# --- ROBUST MOCK DEPENDENCIES ---
def mock_package(name):
    mock = unittest.mock.MagicMock()
    spec = importlib.util.spec_from_loader(name, loader=None)
    mock.__spec__ = spec
    sys.modules[name] = mock
    return mock


mock_package("pocket_tts")
mock_package("pocket_tts.modules.stateful_module")
mock_package("soundfile")
mock_package("transformers")

import psutil
import websockets


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import contextlib

from cohezion.core.persistence.surreal_client import get_surreal_client
from cohezion.simulation.fractal_universe import FractalSimulator
from cohezion.universe.engine import AxiomaticState, UniverseSimulationEngine


logger = logging.getLogger("UniversePrecipitation")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

# --- WEBSOCKET STATE ---
CONNECTED_CLIENTS = set()


async def ws_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        CONNECTED_CLIENTS.remove(websocket)


async def broadcast_telemetry(axiomatic: AxiomaticState, phi: float, tick: int):
    if not CONNECTED_CLIENTS:
        return

    # Map Axiomatic State to Dashboard Schema
    # FIELD (dims 3-5): Tempic, Electric, Magnetic
    # CONTROL (dims 6-8): Rotation, Precession, Charge
    data = {
        "tick": tick,
        "phi_score": phi,
        "coherence": axiomatic.coherence_score(),
        "stability": 1.0 - abs(axiomatic.coherence_score() - 0.5) * 2,
        "friction": axiomatic.field,
        "resonance": axiomatic.precipitation,
        "momentum": axiomatic.control,
        "density": axiomatic.physics,
        "entropy": 1.0 - axiomatic.logic,
        "novelty": axiomatic.novelty,
        "dilation": 1.0,  # Placeholder
        "cpu_load": psutil.cpu_percent(),
        "ram_load": psutil.virtual_memory().percent,
        "vram_load": axiomatic.field * 100.0,  # Proxy
        "bbq_active": False,
    }

    message = json.dumps(data)
    for ws in list(CONNECTED_CLIENTS):
        with contextlib.suppress(Exception):
            await ws.send(message)


class PrecipitationObserver:
    """Displays the 'Minority Report' real-time telemetry in CLI."""

    def __init__(self):
        self.start_time = datetime.now()

    def update(self, journey_id: str, step: int, axiomatic: AxiomaticState, phi: float):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        h_score = 1.0 - abs(axiomatic.coherence_score() - 0.5) * 2

        print("\033[H\033[J", end="")  # Clear screen
        print(f"🌌 COHEZION OBSERVATORY | JOURNEY: {journey_id} | T+{elapsed:.1f}s")
        print("=" * 70)
        print(f"STEP: {step:04d} | PHI SCORE: {phi:.4f} {'🔥' if phi > 0.8 else '❄️'}")
        print(f"STABILITY (HIHO 0.5): {h_score:.4f} {'✅' if h_score > 0.8 else '⚠️'}")
        print("-" * 70)

        print(
            f"SPACE:  X:{axiomatic.spatial_x:+.2f} Y:{axiomatic.spatial_y:+.2f} Z:{axiomatic.spatial_z:+.2f}"
        )
        print(
            f"FIELD:  TMP:{axiomatic.physics:.2f} ELE:{axiomatic.biology:.2f} MAG:{axiomatic.field:.2f}"
        )
        print(
            f"CONTROL: ROT:{axiomatic.logic:.2f} PRE:{axiomatic.quantum:.2f} CHG:{axiomatic.control:.2f}"
        )
        print(
            f"PRECIP:  AWA:{axiomatic.temporal:.2f} PAR:{axiomatic.novelty:.2f} VAL:{axiomatic.precipitation:.2f}"
        )

        print("-" * 70)
        params = axiomatic.to_vector()
        for i in range(0, 12, 4):
            row = params[i : i + 4]
            row_str = "  ".join([f"[{'#' * int(p * 10):10s}] {p:.2f}" for p in row])
            print(row_str)

        print("=" * 70)
        print(f"STATUS: {'REALITY PRECIPITATING...' if phi > 0.7 else 'FLUX STATE ACTIVE'}")
        print(f"WEB UI: ws://localhost:8765 | CLIENTS: {len(CONNECTED_CLIENTS)}")


async def run_precipitation_mission(duration_s: int = 60):
    """Run a high-fidelity mission and capture journeys."""

    # 1. Initialize Substrate
    db = get_surreal_client()
    await db.connect()

    engine = UniverseSimulationEngine(db_client=db)
    observer = PrecipitationObserver()

    # 2. Start Mission Journey
    intent = "Actualize Fractal Toroidal EVO Manifestation across 4 Fabrics"
    journey = await engine.start_journey(agent_name="SovereignPrime", intent=intent)

    # 3. Setup Simulator
    sim = FractalSimulator(num_agents=32)

    logger.info(f"🚀 Mission Started: {journey.id}")

    try:
        for tick in range(1, duration_s * 10):
            sim.step()
            leader = max(sim.agents, key=lambda a: a.cumulative_reward)
            phi = leader.coherence

            # 4. Evolve trajectory in SurrealDB
            point = await engine.evolve_trajectory(
                journey=journey,
                action=f"Stabilize Sector ({leader.x}, {leader.y})",
                result=f"Energy: {leader.energy:.2f}",
                phi_score=phi,
            )

            # 5. Broadcast & Display
            await broadcast_telemetry(point.axiomatic, phi, tick)
            observer.update(journey.id, tick, point.axiomatic, phi)

            await asyncio.sleep(0.1)

        # 6. Finalize Precipitation
        await engine.precipitate_reality(
            journey=journey,
            outputs={"mission_log": "Fractal Manifold Stabilized", "final_phi": leader.coherence},
            phi_score=leader.coherence,
        )
        print("\n✨ MISSION SUCCESS: Reality Precipitated to SurrealDB 3.0")

    except KeyboardInterrupt:
        logger.info("Mission aborted by user.")
    finally:
        await db.close()


async def main(duration_s: int):
    # Start WS Server alongside the mission
    async with websockets.serve(ws_handler, "localhost", 8765):
        await run_precipitation_mission(duration_s)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Universe Precipitation Driver")
    parser.add_argument("--seconds", type=int, default=60, help="Mission duration")
    args = parser.parse_args()

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main(args.seconds))
