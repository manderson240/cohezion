import asyncio
import logging

import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HeartbeatSonification:
    """
    Nexus-Approved Feature: Lightweight Audio Heartbeat.
    Modulates a system beep tempo based on CPU/Memory stress.
    """

    def __init__(self):
        self.running = False

    async def start(self):
        """Starts the audio pulse loop."""
        self.running = True
        logger.info("💓 Heartbeat System Active.")

        while self.running:
            try:
                # 1. Sense Vitals
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory().percent
                stress = max(cpu, mem)

                # 2. Calculate Tempo (BPM)
                # Low stress (10%) -> 60 BPM (1s interval)
                # High stress (90%) -> 180 BPM (0.33s interval)
                bpm = 60 + (stress * 1.5)
                interval = 60.0 / bpm

                # 3. Sonify (Fire & Forget)
                self._beep(stress)

                # 4. Wait
                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Heartbeat Arrhythmia: {e}")
                await asyncio.sleep(1)

    def _beep(self, stress: float):
        """Plays a system beep. Pitch modulates with stress."""
        # Frequency: 440Hz (A4) to 880Hz (A5)
        freq = 440 + (stress * 4)
        length_ms = 100

        # Using 'beep' utility if available, else standard echo bell
        try:
            # Requires 'beep' package: sudo apt install beep
            # subprocess.run(["beep", "-f", str(int(freq)), "-l", str(length_ms)], check=False)
            pass  # Commented out until package verified
        except Exception:
            pass

        # Fallback: Visual Heartbeat Log
        bar = "█" * int(stress / 5)
        print(f"\r💓 [{bar:<20}] {stress}%", end="", flush=True)


if __name__ == "__main__":
    beat = HeartbeatSonification()
    asyncio.run(beat.start())
