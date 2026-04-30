import asyncio
import contextlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import psutil

from .viscoelastic import ViscoelasticController


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
            cls._instance = super().__new__(cls)
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
        self.throttled = False
        self.desperation_active = False
        self.pressure_mitigation_active = False  # Global flag for context pruning
        self.secondary_pids: set[int] = set()
        self.resource_coordinator = None
        self.dilation_factor = 1.0  # 1.0 = Regular speed, 0.1 = Severe Dilation
        self.viscoelastic_controller = ViscoelasticController(relaxation_tau=30.0)
        self._running = True
        self._sandbox_registry: dict[str, int] = {}  # sandbox_id -> memory_mb
        self.service_health: dict[str, str] = {}  # service -> status
        self._initialized = True

        # Initialize cpu_percent to avoid 0.0 on first call
        psutil.cpu_percent(interval=None)

        # Start background heartbeat if loop is running
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                self._heartbeat_task = loop.create_task(self._heartbeat_loop())
        except RuntimeError:
            pass

        logger.info(f"🛡️ ResourceMonitor initialized with max_concurrency={max_concurrency}")

    async def stop(self):
        """Stop the heartbeat loop."""
        self._running = False
        if hasattr(self, "_heartbeat_task"):
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
        logger.info("ResourceMonitor stopped.")

    def register_coordinator(self, coordinator: Any):
        """Register a resource coordinator (e.g. ModelWrangler) for priority handling."""
        self.resource_coordinator = coordinator
        logger.info(f"Registered resource coordinator: {coordinator.__class__.__name__}")

    async def emergency_shutdown(self, vitals: dict[str, Any]):
        """
        Forcefully shutdown high-load processes if system is at risk of lockup.
        Targeting runaway mission processes and unloading Ollama models.
        """
        logger.error(f"🚨 EMERGENCY SHUTDOWN TRIGGERED: {vitals}")

        # 1. Kill runaway missions WITH PREJUDICE (SIGKILL)
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline")
                if not cmdline:
                    continue
                cmd_str = " ".join(cmdline)
                if cmd_str and (
                    "lab_driver.py" in cmd_str
                    or "fractal_nexus_mission.py" in cmd_str
                    or "recursive_improvement_driver.py" in cmd_str
                ):
                    logger.warning(f"KILLED runaway process: {proc.info['pid']} ({cmd_str})")
                    proc.send_signal(9)  # SIGKILL
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 2. Unload Ollama models (Non-privileged)
        if vitals.get("vram_percent", 0) > 85 or vitals["memory_percent"] > 90:
            logger.warning("RAM/VRAM critical. Attempting to unload Ollama models...")
            try:
                # Use Ollama API to unload all models
                # First, get running models
                process = await asyncio.create_subprocess_exec(
                    "curl",
                    "-s",
                    "http://localhost:11434/api/ps",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await process.communicate()
                if stdout:
                    data = json.loads(stdout)
                    for model in data.get("models", []):
                        name = model.get("name")
                        logger.info(f"Unloading Ollama model: {name}")
                        await asyncio.create_subprocess_exec(
                            "curl",
                            "-s",
                            "-X",
                            "POST",
                            "http://localhost:11434/api/generate",
                            "-d",
                            json.dumps({"model": name, "keep_alive": 0}),
                        )
            except Exception as e:
                logger.error(f"Failed to unload Ollama models: {e}")

    async def unload_model(self, model_name: str):
        """Unload a specific Ollama model to free VRAM."""
        logger.info(f"Unloading model: {model_name}")
        try:
            await asyncio.create_subprocess_exec(
                "curl",
                "-s",
                "-X",
                "POST",
                "http://localhost:11434/api/generate",
                "-d",
                json.dumps({"model": model_name, "keep_alive": 0}),
            )
        except Exception as e:
            logger.error(f"Failed to unload model {model_name}: {e}")

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
            if (
                vitals["cpu_percent"] > 90
                or vitals["memory_percent"] > 90
                or vitals.get("vram_percent", 0) > 90
            ):
                wait_time = 10.0
                logger.warning(
                    f"⚠️ Extreme System Pressure Detected: {vitals}. Throttling for {wait_time}s..."
                )
                self.throttled = True
                await asyncio.sleep(wait_time)
            else:
                self.throttled = False

        await self.semaphore.acquire()
        self.active_calls += 1
        logger.debug(f"Slot acquired. Active calls: {self.active_calls}")

    def release_capacity(self):
        """Release a concurrency slot."""
        self.semaphore.release()
        self.active_calls -= 1
        logger.debug(f"Slot released. Active calls: {self.active_calls}")

    def register_sandbox(self, sandbox_id: str, memory_mb: int) -> None:
        """Register an active sandbox for resource tracking.

        Parameters
        ----------
        sandbox_id : str
            Unique identifier for the sandbox.
        memory_mb : int
            Memory allocated to this sandbox in megabytes.
        """
        self._sandbox_registry[sandbox_id] = memory_mb
        logger.info(
            (
                f"Sandbox registered: {sandbox_id} ({memory_mb}MB). Total sandbox memory: "
                f"{self.total_sandbox_memory_mb}MB"
            )
        )

    def deregister_sandbox(self, sandbox_id: str) -> None:
        """Deregister a sandbox that has completed or been terminated.

        Parameters
        ----------
        sandbox_id : str
            Unique identifier for the sandbox to remove.
        """
        removed = self._sandbox_registry.pop(sandbox_id, None)
        if removed is not None:
            logger.info(
                (
                    f"Sandbox deregistered: {sandbox_id}. Total sandbox memory: "
                    f"{self.total_sandbox_memory_mb}MB"
                )
            )

    @property
    def total_sandbox_memory_mb(self) -> int:
        """Total memory allocated across all registered sandboxes."""
        return sum(self._sandbox_registry.values())

    def get_vitals(self) -> dict[str, Any]:
        """Fetch current system usage stats including AMD VRAM and sandbox info."""
        vm = psutil.virtual_memory()
        vitals = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": vm.percent,
            "memory_available_gb": vm.available / (1024**3),
            "active_llm_calls": self.active_calls,
            "timestamp": time.time(),
            "vram_percent": self._get_vram_usage(),
            "dilation_factor": self.dilation_factor,
            "active_sandboxes": len(self._sandbox_registry),
            "sandbox_memory_mb": self.total_sandbox_memory_mb,
            "service_health": self.service_health,
        }
        return vitals

    def get_dilation_factor(self) -> float:
        """Get the current simulation backpressure (dilation) factor."""
        return self.dilation_factor

    def _get_vram_usage(self) -> float:
        """Fetch GPU memory pressure for AMD GPU.

        On unified memory iGPU (e.g. Radeon 8060S / Strix Halo), the sysfs
        ``mem_info_vram_total`` reports a tiny dedicated carveout (~512 MiB)
        that is always nearly full.  This is NOT indicative of real memory
        pressure.  Instead we check the GTT (Graphics Translation Table)
        which represents the actual unified memory pool shared with system
        RAM.  If GTT sysfs is unavailable, fall back to system RAM usage
        which is equivalent on UMA hardware.
        """
        try:
            # Dynamically discover AMD GPU device path
            gpu_paths = list(Path("/sys/class/drm/").glob("card*/device"))
            device = None
            for p in gpu_paths:
                vendor_path = p / "vendor"
                if vendor_path.exists() and vendor_path.read_text().strip() == "0x1002":
                    device = p
                    break

            if not device:
                # Fallback to default if discovery fails
                device = Path("/sys/class/drm/card1/device")

            # Prefer GTT (unified memory pool) over dedicated VRAM carveout
            gtt_total_path = device / "mem_info_gtt_total"
            gtt_used_path = device / "mem_info_gtt_used"
            if gtt_total_path.exists() and gtt_used_path.exists():
                gtt_total = int(gtt_total_path.read_text().strip())
                gtt_used = int(gtt_used_path.read_text().strip())
                if gtt_total > 0:
                    return (gtt_used / gtt_total) * 100.0

            # Fallback: dedicated VRAM (only useful for discrete GPUs)
            vram_total_path = device / "mem_info_vram_total"
            vram_used_path = device / "mem_info_vram_used"
            if vram_total_path.exists() and vram_used_path.exists():
                vram_total = int(vram_total_path.read_text().strip())
                vram_used = int(vram_used_path.read_text().strip())
                # Skip tiny carveouts (<4 GiB) -- they are iGPU framebuffers,
                # not real VRAM pools.  Use system RAM instead.
                if vram_total >= 4 * (1024**3) and vram_total > 0:
                    return (vram_used / vram_total) * 100.0

        except Exception as e:
            logger.debug("VRAM usage read failed: %s", e)
        return 0.0

    async def enter_desperation_mode(self, vitals: dict[str, Any]):
        """
        Dampen non-essential activity using non-privileged niceness and SIGSTOP.
        """
        if self.desperation_active:
            return

        logger.warning(f"💥 ENTERING DESPERATION MODE (System Pressure: {vitals})")
        self.desperation_active = True
        self.secondary_pids = self._identify_secondary_processes()

        for pid in self.secondary_pids:
            try:
                p = psutil.Process(pid)
                # Tier 1: Max Niceness
                p.nice(19)
                # Tier 2: SIGSTOP if pressure is extreme (93%+)
                if vitals["cpu_percent"] > 93 or vitals["memory_percent"] > 93:
                    logger.info(f"Pausing process {pid} (SIGSTOP)")
                    p.send_signal(19)  # SIGSTOP
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    async def exit_desperation_mode(self):
        """Restore normal operation to damped processes."""
        if not self.desperation_active:
            return

        logger.info("🌈 System pressure stabilized. Exiting Desperation Mode.")
        for pid in list(self.secondary_pids):
            try:
                p = psutil.Process(pid)
                p.send_signal(18)  # SIGCONT
                p.nice(0)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        self.secondary_pids.clear()
        self.desperation_active = False

    def _identify_secondary_processes(self) -> set[int]:
        """Find PIDs of non-essential background simulations and scouts."""
        pids = set()
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info.get("cmdline", []) or [])
                if any(
                    x in cmdline
                    for x in [
                        "fractal_universe.py",
                        "research_task.py",
                        "scout",
                        "recursive_improvement_driver.py",
                    ]
                ):
                    pids.add(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return pids

    async def _check_service_health(self):
        """Autonomic health check for core services (Connectivity Squad)."""
        services = {
            "SurrealDB": "http://localhost:8000/health",
            "Cloud Vault": "http://localhost:8360/health",
            "Ollama": "http://localhost:11434/api/tags",
            "Obsidian": "http://localhost:22360/",
        }

        async def _check_single(name, url):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "curl",
                    "-s",
                    "-o",
                    "/dev/null",
                    "-w",
                    "%{http_code}",
                    url,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=1.0)
                status = stdout.decode().strip()
                self.service_health[name] = "UP" if status in ("200", "404") else "DOWN"
            except Exception:
                self.service_health[name] = "LOST"

        # Run checks in parallel to maintain heartbeat timing
        await asyncio.gather(*[_check_single(n, u) for n, u in services.items()])

    async def _heartbeat_loop(self):
        """Background loop to log system health and monitor for stalled processes."""
        self.last_heartbeat = time.time()
        while self._running:
            await self._check_service_health()
            vitals = self.get_vitals()
            self.last_heartbeat = time.time()

            cpu = vitals["cpu_percent"]
            ram = vitals["memory_percent"]
            vram = vitals["vram_percent"]

            # 1. Calculate Viscous Adjustment (Maxwellian Relaxation)
            viscous_correction = self.viscoelastic_controller.calculate_dilation_adjustment(
                cpu, ram, vram
            )

            # 2. Determine Base Dilation Factor (Tiered Thresholds)
            if cpu > 90 or ram > 90 or vram > 90:
                logger.error(f"🚑 EMERGENCY SYSTEM PRESSURE (Tier 3): {vitals}")
                await self.emergency_shutdown(vitals)
                self.dilation_factor = 0.01  # Near halt
            elif cpu > 85 or ram > 85 or vram > 85:
                logger.warning(f"⚠️ DESPERATION PRESSURE (Step 3 Throttling): {vitals}")
                await self.enter_desperation_mode(vitals)
                self.throttled = True
                self.dilation_factor = 0.05
            elif cpu > 75 or ram > 75 or vram > 75:
                logger.warning(f"🔍 HIGH PRESSURE (Tier 2): {vitals}")
                await self.exit_desperation_mode()
                self.throttled = True
                self.dilation_factor = 0.3
            elif cpu > 60 or ram > 60 or vram > 60:
                self.dilation_factor = 0.6
                self.throttled = False
                await self.exit_desperation_mode()
            else:
                await self.exit_desperation_mode()
                self.throttled = False
                self.dilation_factor = 1.0

            # 3. Apply Viscous Damping (Proactive slowdown)
            self.dilation_factor = max(0.01, self.dilation_factor - viscous_correction)

            # Sandbox pressure warning
            sandbox_mem = self.total_sandbox_memory_mb
            if sandbox_mem > 80 * 1024:  # >80GB sandbox memory
                logger.warning(
                    (
                        f"Sandbox memory pressure: {sandbox_mem}MB allocated across "
                        f"{len(self._sandbox_registry)} sandboxes"
                    )
                )

            log_entry = (
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"CPU: {cpu}% | RAM: {ram}% | VRAM: {vram:.1f}% | "
                f"LLM Calls: {vitals['active_llm_calls']} | Dilation: {self.dilation_factor} | "
                f"Services: {self.service_health} | "
                f"Sandboxes: {len(self._sandbox_registry)} ({sandbox_mem}MB)\n"
            )

            # Use thread for blocking file I/O to avoid event loop latency
            await asyncio.to_thread(self._append_log, log_entry)

            await asyncio.sleep(2)  # Tight 2s loop for Framework 16 stability

    def _append_log(self, entry: str):
        """Synchronous log append for use in thread."""
        with open(self.heartbeat_log, "a") as f:
            f.write(entry)

    def checkpoint_active_mission(self, data: dict[str, Any], mission_id: str):
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
