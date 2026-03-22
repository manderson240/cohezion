import asyncio
import contextlib
import json
import logging
import math
import random
import time

import psutil
import websockets


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [Telem] - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("TelemetryServer")

CONNECTED_CLIENTS = set()


async def ws_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        CONNECTED_CLIENTS.remove(websocket)


async def broadcast_loop():
    logger.info("📡 Telemetry Server Started on localhost:8765")
    start_time = time.time()

    while True:
        t = time.time() - start_time

        # 1. Check BBQ Status (REAL)
        bbq_active = False
        for p in psutil.process_iter(["name", "cmdline"]):
            try:
                cmd = p.info.get("cmdline") or []
                if any("autonomous_bbq.py" in str(c) for c in cmd):
                    bbq_active = True
                    break
            except Exception:
                pass

        # 2. Fabricate 12D Physics (Simulated for Visuals)
        # Coherence oscillates around 0.5 (HIHO Stability)
        coherence = 0.5 + 0.1 * math.sin(t * 0.5) + random.uniform(-0.01, 0.01)
        entropy = 0.5 - 0.1 * math.sin(t * 0.3)

        # Scrape Real Thought from Log
        latest_thought = "BBQ ACTIVE: Monitoring System Vitals..."
        try:
            with open("autonomous_bbq.log") as f:
                # Read last 2KB for efficiency
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 2048))
                lines = f.readlines()
                for line in reversed(lines):
                    if "💭 Thought:" in line:
                        latest_thought = line.split("💭 Thought:")[-1].strip()
                        break
        except Exception:
            pass

        data = {
            "title": "FRACTAL NEXUS TELEMETRY",
            "cpu_load": psutil.cpu_percent(),
            "ram_load": psutil.virtual_memory().percent,
            "vram_load": 93.0,
            "coherence": coherence,
            "drift": 0.01 * random.random(),
            "stability": 1.0 - abs(coherence - 0.5),
            "entropy": entropy,
            "novelty": random.random(),
            "friction": 0.1,
            "momentum": 0.8,
            "density": 1.0,
            "resonance": 0.9,
            "dilation": 0.05 if bbq_active else 1.0,
            "bbq_active": bbq_active,
            "message": latest_thought,
            "narration": latest_thought,  # For Audio Engine
        }

        msg = json.dumps(data)

        if CONNECTED_CLIENTS:
            for ws in list(CONNECTED_CLIENTS):
                with contextlib.suppress(BaseException):
                    await ws.send(msg)

        # Log occasionally
        if int(t) % 10 == 0:
            logger.info(f"Broadcast: Clients={len(CONNECTED_CLIENTS)} | BBQ={bbq_active} | Coh={coherence:.3f}")

        await asyncio.sleep(0.1)  # 10Hz Update


async def main():
    async with websockets.serve(ws_handler, "localhost", 8765):
        await broadcast_loop()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
