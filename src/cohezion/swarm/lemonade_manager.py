"""Private Lemonade Server lifecycle manager for embeddable execution."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from pathlib import Path


logger = logging.getLogger(__name__)

# RAM safety buffer: keep this much free before starting lemond (bytes).
# The 2026-06-09 OOM crash happened with only 81 GB free and a large model load.
# 20 GB buffer covers the OmniRouter's own KV cache + OS page cache headroom.
_MIN_FREE_RAM_BYTES = 20 * 1024**3  # 20 GiB


def _free_ram_bytes() -> int:
    """Return available RAM in bytes from /proc/meminfo MemAvailable."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024  # kB → bytes
    except Exception:
        pass
    return 2**63  # unknown → allow (fail-open)


class LemonadeManager:
    """Manages the private embeddable Lemonade server instance."""

    def __init__(
        self,
        base_dir: str | Path | None = None,
        port: int = 13305,
        host: str = "localhost",
        min_free_ram_bytes: int = _MIN_FREE_RAM_BYTES,
    ) -> None:
        self.base_dir = Path(base_dir or "vendor/lemonade").absolute()
        self.port = port
        self.host = host
        self.process: subprocess.Popen | None = None
        self._executable = self.base_dir / "lemond"
        self._min_free_ram = min_free_ram_bytes

    async def start(self) -> bool:
        """Spawn the lemond process — guarded by pre-launch RAM check."""
        if self.process and self.process.poll() is None:
            logger.info("Lemonade server already running (PID %d)", self.process.pid)
            return True

        if not self._executable.exists():
            logger.error("Lemonade executable not found at %s", self._executable)
            return False

        # OOM guard (N3): refuse to start if available RAM is below the safety floor.
        free = _free_ram_bytes()
        if free < self._min_free_ram:
            logger.error(
                "OOM guard: refusing to start lemond — only %.1f GiB free (need %.1f GiB). "
                "Free memory or reduce loaded models before retrying.",
                free / 1024**3,
                self._min_free_ram / 1024**3,
            )
            return False

        logger.info(
            "RAM check passed: %.1f GiB free (threshold %.1f GiB)",
            free / 1024**3,
            self._min_free_ram / 1024**3,
        )

        # Prepare environment
        env = os.environ.copy()
        # Add local bin to LD_LIBRARY_PATH to ensure optimized libs are loaded
        local_bin = str(self.base_dir / "bin")
        if "LD_LIBRARY_PATH" in env:
            env["LD_LIBRARY_PATH"] = f"{local_bin}:{env['LD_LIBRARY_PATH']}"
        else:
            env["LD_LIBRARY_PATH"] = local_bin

        logger.info("Starting private Lemonade server on port %d...", self.port)
        try:
            # We use subprocess.Popen instead of asyncio.create_subprocess_exec
            # for easier integration with existing synchronous shutdown hooks if needed,
            # but we run it in a way that doesn't block.
            self.process = subprocess.Popen(
                [
                    str(self._executable),
                    str(self.base_dir),
                    "--port",
                    str(self.port),
                    "--host",
                    self.host,
                ],
                cwd=self.base_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Brief wait to check for immediate failure
            await asyncio.sleep(2)
            if self.process.poll() is not None:
                output = self.process.stdout.read() if self.process.stdout else ""
                logger.error("Lemonade server failed to start immediately. Output:\n%s", output)
                return False

            logger.info("Lemonade server started (PID %d)", self.process.pid)
            return True
        except Exception as e:
            logger.error("Failed to spawn Lemonade server: %s", e)
            return False

    async def stop(self) -> None:
        """Terminate the lemond process."""
        if not self.process:
            return

        logger.info("Stopping Lemonade server (PID %d)...", self.process.pid)
        self.process.terminate()
        try:
            # Give it some time to shut down gracefully
            for _ in range(5):
                if self.process.poll() is not None:
                    break
                await asyncio.sleep(1)
            else:
                logger.warning("Lemonade server didn't stop gracefully, killing...")
                self.process.kill()
        except Exception as e:
            logger.error("Error during Lemonade server shutdown: %s", e)
        finally:
            self.process = None

    def is_running(self) -> bool:
        """Check if the process is active."""
        return self.process is not None and self.process.poll() is None

    async def wait_until_ready(self, timeout: float = 30.0) -> bool:
        """Wait for the server to respond to health checks."""
        import httpx

        url = f"http://{self.host}:{self.port}/api/v1/models"
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=1.0)
                    if resp.status_code == 200:
                        return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(1)
        return False
