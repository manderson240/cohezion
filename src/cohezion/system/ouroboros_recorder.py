
import asyncio
import logging
import time
from typing import Any, Dict
from datetime import datetime

from cohezion.db.admin import DBAdmin
from cohezion.reliability.monitor import get_resource_monitor
from cohezion.swarm.git_health import get_repo_bloat

logger = logging.getLogger(__name__)

class OuroborosRecorder:
    """
    Ouroboros Sensor Fusion Recorder.
    
    Acts as a 'Flight Recorder' for the Cohezion system, fusing:
    1. Hardware Vitals (CPU, RAM, VRAM, GTT) from ResourceMonitor.
    2. Software Health (Git Entropy, Bloat) from GitHealth.
    3. System Dilation Factor.
    
    Persists data to 'system_pulse' table in SurrealDB every interval.
    """
    
    def __init__(self, interval_seconds: int = 10):
        self.interval = interval_seconds
        self.dba = DBAdmin()
        self.monitor = get_resource_monitor()
        self._running = False
        self._task = None

    async def start(self):
        """Start the background recording loop."""
        if self._running:
            return
        
        # Ensure DB connection
        await self.dba.connect()
        self._running = True
        self._task = asyncio.create_task(self._record_loop())
        logger.info("🔴 Ouroboros Recorder STARTED.")

    async def stop(self):
        """Stop the recorder."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("⚫ Ouroboros Recorder STOPPED.")

    async def _record_loop(self):
        while self._running:
            try:
                start_time = time.perf_counter()
                
                # 1. Collect Hardware Vitals
                hw_vitals = self.monitor.get_vitals()
                dilation = self.monitor.get_dilation_factor()
                
                # 2. Collect Software Sensors
                logger.info("Reading Git Health...")
                try:
                    loop = asyncio.get_running_loop()
                    sw_vitals = await asyncio.wait_for(
                        loop.run_in_executor(None, get_repo_bloat),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Git Health Sensor timed out (Repo too large?)")
                    sw_vitals = {"error": "timeout"}
                
                # 3. Fuse Data
                logger.info(f"Fusing Data (HW: {len(hw_vitals)} keys, SW: {len(sw_vitals)} keys)")
                pulse_packet = {
                    # Let SurrealDB handle timestamp with time::now()
                    # "timestamp": datetime.now().isoformat(), 
                    "hardware": hw_vitals,
                    "software": sw_vitals,
                    "dilation_factor": dilation
                }
                
                # 4. Persist
                # Using create() to generate a new time-series record
                res = await self.dba.client.create("system_pulse", pulse_packet)
                logger.info(f"💾 Pulse Saved: {res}")
                
                # 5. Wait for next interval
                elapsed = time.perf_counter() - start_time
                await asyncio.sleep(max(1.0, self.interval - elapsed))
                
            except Exception as e:
                logger.error(f"Ouroboros Recording Failed: {e}")
                await asyncio.sleep(self.interval)

            # --- PHASE 21: Auto-Evolution Loop ---
            # Periodically (every 100 cycles approx, or just chance) trigger reflex
            # For "Million Loops", we want it frequent but safe.
            # Using 1% chance per tick (approx once per 1000s if tick=10s) 
            # OR simple counter. Let's use a counter.
            if not hasattr(self, '_reflex_counter'):
                self._reflex_counter = 0
            
            self._reflex_counter += 1
            if self._reflex_counter >= 30: # Every ~5 minutes (30 * 10s)
                self._reflex_counter = 0
                try:
                    # Lazy import to avoid circular dep at module level if any
                    from cohezion.evolution.reflex import ReflexAgent
                    if not hasattr(self, '_reflex_agent'):
                        self._reflex_agent = ReflexAgent()
                    
                    logger.info("🧠 Triggering Reflex Cycle...")
                    # Run as background task to not block recording
                    asyncio.create_task(self._reflex_agent.scan_and_reflect())
                except Exception as e:
                    logger.error(f"Reflex trigger failed: {e}")

if __name__ == "__main__":
    # Simple standalone test
    async def main():
        logging.basicConfig(level=logging.INFO)
        rec = OuroborosRecorder(interval_seconds=2)
        await rec.start()
        await asyncio.sleep(15) # Increased wait to allow for timeout + insert
        await rec.stop()
    
    asyncio.run(main())
