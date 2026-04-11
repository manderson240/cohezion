import asyncio
import logging

from cohezion.system.ganglion import OuroborosGanglion


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/ouroboros.log"), logging.StreamHandler()],
)
logger = logging.getLogger("OuroborosDaemon")

import json

import websockets


# WS Clients
CONNECTED_CLIENTS = set()


async def ws_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        CONNECTED_CLIENTS.remove(websocket)


import contextlib

import psutil


async def broadcast_state(state):
    if not CONNECTED_CLIENTS:
        return

    # Check for BBQ
    bbq_active = False
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            if "autonomous_bbq.py" in (p.info.get("cmdline") or []):
                bbq_active = True
                break
        except Exception:
            pass

    # Create simple dict for JSON serialization
    data = {
        "cpu_load": state.cpu_load,
        "ram_load": state.ram_load,
        "vram_load": state.vram_load,
        "coherence": state.coherence,
        "drift": state.drift,
        "stability": state.stability,
        "entropy": state.entropy,
        "novelty": state.novelty,
        "friction": state.friction,
        "momentum": state.momentum,
        "density": state.density,
        "resonance": state.resonance,
        "dilation": state.dilation,
        "bbq_active": bbq_active,
    }
    message = json.dumps(data)
    for ws in list(CONNECTED_CLIENTS):
        with contextlib.suppress(Exception):
            await ws.send(message)


async def ouroboros_loop():
    """
    The Main Autonomic Loop.
    1. Sense (Perceive State)
    2. Feel (Evaluate Stability)
    3. Act (Trigger Reflex)
    4. Sleep (Reset)
    """
    ganglion = OuroborosGanglion()

    logger.info("🐍 OUROBOROS DAEMON STARTED")
    logger.info("   Target Coherence: 0.5")
    logger.info("   Actuators: ShadowScripter (Dream), TestMycelium (Stabilize)")
    logger.info("   Pulse Stream: ws://localhost:8765")

    while True:
        try:
            # 1. SENSE
            state = await ganglion.sense.perceive()

            # 2. ACT
            reaction = await ganglion.reflex(state)

            logger.info(
                f"💓 Heartbeat: Stability={state.stability:.2f} | Drifts={state.drift:.2f} | Reflex={reaction}"
            )

            # 3. BROADCAST
            await broadcast_state(state)

            # 4. SLEEP
            # We sleep for 10s to avoid overwhelming the local machine
            await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"❌ Ouroboros Crash: {e}", exc_info=True)
            await asyncio.sleep(5)  # Backoff


async def main():
    # Start WS Server
    async with websockets.serve(ws_handler, "localhost", 8765):
        await ouroboros_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Ouroboros Stopped manually.")
