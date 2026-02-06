import asyncio
import logging
import subprocess
import time
from pathlib import Path

import psutil

# Configure logging
logging.basicConfig(
    filename="logs/startup.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Component Definitions
COMPONENTS = {
    "surrealdb": {
        "cmd_signature": "surreal",
        "port": 8000,
        "start_cmd": [
            "surreal",
            "start",
            "--log",
            "debug",
            "--user",
            "root",
            "--pass",
            "root",
            "file:cohezion.core.persistence",
        ],
        "cwd": ".",
    },
    "api": {
        "cmd_signature": "uvicorn cohezion.api:app",
        "port": 8080,
        "start_cmd": [
            "uv",
            "run",
            "uvicorn",
            "cohezion.api:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
        ],
        "cwd": "src",  # relative to project root, handled in code
    },
    "recorder": {
        "cmd_signature": "ouroboros_recorder.py",
        "port": None,
        "start_cmd": [
            "uv",
            "run",
            "python3",
            "src/cohezion/system/ouroboros_recorder.py",
        ],
        "cwd": ".",
    },
    "simulation": {
        "cmd_signature": "universe_sim_agent.py",
        "port": 5000,
        "start_cmd": [
            "uv",
            "run",
            "python3",
            "src/cohezion/swarm/agents/universe_sim_agent.py",
        ],
        "cwd": ".",
    },
    "webapp": {
        "cmd_signature": "vite",
        "port": 5173,
        "start_cmd": ["npm", "run", "dev"],
        "cwd": "apps/webapp",
    },
}


class DaemonManager:
    """Manages the lifecycle of Cohezion background processes."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.logs_dir = self.project_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)

    def is_running(self, signature: str) -> bool:
        """Check if a process with the given signature is running."""
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline", [])
                cmd_str = " ".join(cmdline) if cmdline else ""
                if signature in cmd_str:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False

    def start_component(self, name: str):
        """Start a specific component."""
        config = COMPONENTS.get(name)
        if not config:
            logger.error(f"Unknown component: {name}")
            return False

        if self.is_running(config["cmd_signature"]):
            logger.info(f"🟢 {name.upper()} is already running.")
            return True

        logger.info(f"🟡 Starting {name.upper()}...")
        try:
            cwd = (
                self.project_root / config["cwd"]
                if config["cwd"] != "."
                else self.project_root
            )

            # Redirect stdout/stderr to log files
            log_out = open(self.logs_dir / f"{name}_out.log", "a")
            log_err = open(self.logs_dir / f"{name}_err.log", "a")

            subprocess.Popen(
                config["start_cmd"],
                cwd=cwd,
                stdout=log_out,
                stderr=log_err,
                start_new_session=True,  # Detach
            )
            time.sleep(2)  # Wait for startup

            if self.is_running(config["cmd_signature"]):
                logger.info(f"✅ {name.upper()} started successfully.")
                print(f"✅ {name.upper()} started.")
                return True
            else:
                logger.error(f"❌ {name.upper()} failed to start (check logs).")
                print(f"❌ {name.upper()} failed to start.")
                return False

        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
            return False

    async def wait_for_service(self, name: str, port: int, timeout: int = 30) -> bool:
        """Wait for a TCP port to become available."""
        import socket

        start_time = time.time()
        logger.info(f"⏳ Waiting for {name} on port {port}...")

        while time.time() - start_time < timeout:
            try:
                with socket.create_connection(("localhost", port), timeout=1):
                    logger.info(f"✅ {name} available on port {port}")
                    return True
            except (OSError, ConnectionRefusedError):
                await asyncio.sleep(0.5)

        logger.error(f"❌ Timed out waiting for {name}:{port}")
        return False

    def kill_orphans(self):
        """Kill any existing processes that match our signatures."""
        logger.info("🧟 Hunting for zombies...")
        count = 0
        for config in COMPONENTS.values():
            sig = config["cmd_signature"]
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    cmd_str = " ".join(cmdline) if cmdline else ""
                    if sig in cmd_str:
                        logger.warning(f"Killing orphan {proc.info['pid']}: {cmd_str}")
                        proc.kill()
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        if count > 0:
            logger.info(f"💀 Killed {count} zombies.")
            time.sleep(1)  # Allow OS to reclaim resources
        else:
            logger.info("✨ No zombies found.")

    async def _async_wake_up(self):
        """Async wake up logic."""
        print("🌅 Waking up Cohezion System...")

        # 1. Clean Slate
        self.kill_orphans()

        # 2. Start Brain (DB)
        if self.start_component("surrealdb"):
            await self.wait_for_service("SurrealDB", 8000)

        # 3. Start Voice (API)
        if self.start_component("api"):
            await self.wait_for_service("API", 8080)

        # 4. Start Physics (Simulation)
        if self.start_component("simulation"):
            await self.wait_for_service("Simulation", 5000)

        # 5. Start Visuals (Webapp)
        if self.start_component("webapp"):
            await self.wait_for_service("Webapp", 5173)

        # 6. Start Autonomics (Recorder)
        self.start_component("recorder")

        print(f"🟢 System Online. Logs at {self.logs_dir}")

    def wake_up(self):
        """Entry point."""
        asyncio.run(self._async_wake_up())


def get_daemon_manager():
    return DaemonManager()


if __name__ == "__main__":
    dm = DaemonManager()
    dm.wake_up()
