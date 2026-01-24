import asyncio
import logging
import psutil
import time
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """
    Global Resource Monitor & Concurrency Guard (Gateway 33).

    Prevents system lockups by:
    1. Enforcing global LLM concurrency limits.
    2. Monitoring CPU/RAM/VRAM pressure.
    3. Providing backpressure signals to agents.
    """
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ResourceMonitor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_concurrency: int = 4):
        if self._initialized:
            return
        self.max_concurrency = max_concurrency
        self.active_calls = 0
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.heartbeat_log = Path("logs/system_heartbeat.log")
        self.heartbeat_log.parent.mkdir(parents=True, exist_ok=True)
        self.critical_pressure = False
        self._initialized = True

        # Start background heartbeat if loop is running
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                loop.create_task(self._heartbeat_loop())
        except RuntimeError:
            pass

        logger.info(f"🛡️ ResourceMonitor initialized with max_concurrency={max_concurrency}")

    async def emergency_shutdown(self, vitals: Dict[str, Any]):
        """
        Forcefully shutdown high-load processes if system is at risk of lockup.
        Targeting fractal_nexus_mission.py and large Ollama models if RAM > 95%.
        """
        logger.error(f"🚨 EMERGENCY SHUTDOWN TRIGGERED: {vitals}")

        # 1. Kill the mission if running
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and "fractal_nexus_mission.py" in " ".join(cmdline):
                    logger.warning(f"Killing runaway mission process: {proc.info['pid']}")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 2. Stop Ollama if RAM is extremely critical
        if vitals["memory_percent"] > 98:
            logger.warning("RAM critical (>98%). Stopping ollama service...")
            try:
                subprocess.run(["sudo", "systemctl", "stop", "ollama"], check=False)
            except Exception as e:
                logger.error(f"Failed to stop ollama: {e}")

    async def _ensure_heartbeat(self):
        """Ensure heartbeat loop is running."""
        if not hasattr(self, "_heartbeat_task") or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def wait_for_capacity(self):
        """Async wait until concurrency slot is available."""
        await self._ensure_heartbeat()
        async with self._lock:
            # Check system vitals before proceeding
            vitals = self.get_vitals()
            if vitals["cpu_percent"] > 90 or vitals["memory_percent"] > 90:
                wait_time = 5.0
                logger.warning(f"⚠️ Extreme System Pressure Detected: {vitals}. Throttling for {wait_time}s...")
                await asyncio.sleep(wait_time)

        await self.semaphore.acquire()
        self.active_calls += 1
        logger.debug(f"Slot acquired. Active calls: {self.active_calls}")

    def release_capacity(self):
        """Release a concurrency slot."""
        self.semaphore.release()
        self.active_calls -= 1
        logger.debug(f"Slot released. Active calls: {self.active_calls}")

    def get_vitals(self) -> Dict[str, Any]:
        """Fetch current system usage stats."""
        vm = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": vm.percent,
            "memory_available_gb": vm.available / (1024**3),
            "active_llm_calls": self.active_calls,
            "timestamp": time.time()
        }

    async def _heartbeat_loop(self):
        """Background loop to log system health and monitor for stalled processes."""
        self.last_heartbeat = time.time()
        while True:
            vitals = self.get_vitals()
            self.last_heartbeat = time.time()

            # Detect emergency pressure
            self.critical_pressure = (vitals["cpu_percent"] > 95 or vitals["memory_percent"] > 95)

            log_entry = (
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"CPU: {vitals['cpu_percent']}% | "
                f"RAM: {vitals['memory_percent']}% ({vitals['memory_available_gb']:.1f}GB free) | "
                f"LLM Calls: {vitals['active_llm_calls']}\n"
            )

            with open(self.heartbeat_log, "a") as f:
                f.write(log_entry)

            if self.critical_pressure:
                logger.error(f"🚑 EMERGENCY SYSTEM PRESSURE: {vitals}")
                if vitals["memory_percent"] > 95:
                    await self.emergency_shutdown(vitals)

            # Heartbeat Shadowing: If we haven't updated in >30s, something is blocking the loop
            # In a real async environment, this would be checked by a separate watchdog thread
            # For now, we'll log it for external monitoring

            await asyncio.sleep(10)

    def checkpoint_active_mission(self, data: Dict[str, Any], mission_id: str):
        """
        Placeholder for SurrealDB checkpointing.
        Saves simulation state to prevent data loss.
        """
        logger.info(f"💾 Checkpointing mission {mission_id}...")
        # Implementation would use SurrealDB client here
        pass

def get_resource_monitor() -> ResourceMonitor:
    """Get the global ResourceMonitor instance."""
    return ResourceMonitor()
