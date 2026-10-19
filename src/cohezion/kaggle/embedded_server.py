"""Embedded Inference Server Lifecycle Manager for Kaggle Environments.

Enables running offline OpenAI-compatible local daemons (e.g. Lemonade lemond, llama-server)
directly inside airgapped Kaggle notebook containers (Internet: Off).
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx


logger = logging.getLogger(__name__)


@dataclass
class EmbeddedServerConfig:
    """Configuration for embedded server execution inside Kaggle."""

    host: str = "127.0.0.1"
    port: int = 13305
    binary_path: Path | None = None
    model_path: Path | None = None
    n_gpu_layers: int = 33
    ctx_size: int = 8192
    timeout_s: float = 30.0
    extra_args: list[str] = field(default_factory=list)


class EmbeddedServerManager:
    """Manages the background lifecycle of an embedded inference daemon."""

    def __init__(self, config: EmbeddedServerConfig | None = None) -> None:
        self.config = config or EmbeddedServerConfig()
        self.process: subprocess.Popen[bytes] | None = None
        self._registered_cleanup = False

    @staticmethod
    def is_kaggle_environment() -> bool:
        """Determines if execution is occurring within a Kaggle container."""
        return os.path.exists("/kaggle/input") or os.path.exists("/kaggle/working")

    @classmethod
    def locate_offline_binary(cls, default_name: str = "lemond") -> Path | None:
        """Searches /kaggle/input and local vendor trees for the server binary."""
        # 1. Check PATH
        path_binary = shutil.which(default_name) or shutil.which("llama-server")
        if path_binary:
            return Path(path_binary)

        # 2. Check Kaggle input dataset directories
        kaggle_input = Path("/kaggle/input")
        if kaggle_input.exists():
            for candidate in kaggle_input.rglob(default_name):
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return candidate
            for candidate in kaggle_input.rglob("llama-server"):
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return candidate

        # 3. Check local vendor directory
        vendor_dir = Path("vendor")
        if vendor_dir.exists():
            for candidate in vendor_dir.rglob(default_name):
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return candidate

        return None

    @classmethod
    def locate_offline_weights(cls, pattern: str = "*.gguf") -> Path | None:
        """Searches /kaggle/input and local cache for model weights."""
        kaggle_input = Path("/kaggle/input")
        if kaggle_input.exists():
            for candidate in kaggle_input.rglob(pattern):
                if candidate.is_file():
                    return candidate

        # Local fallback search
        local_models = Path("models")
        if local_models.exists():
            for candidate in local_models.rglob(pattern):
                if candidate.is_file():
                    return candidate

        return None

    def start(self) -> bool:
        """Launches the server daemon in the background and verifies health."""
        if self.is_healthy():
            logger.info("Embedded server is already responsive on port %d", self.config.port)
            return True

        binary = self.config.binary_path or self.locate_offline_binary()
        if not binary or not binary.exists():
            logger.warning("No embedded server binary found. Offline server bootstrap skipped.")
            return False

        model = self.config.model_path or self.locate_offline_weights()
        cmd = [
            str(binary),
            "--host",
            self.config.host,
            "--port",
            str(self.config.port),
            "-c",
            str(self.config.ctx_size),
        ]

        if model and model.exists():
            cmd.extend(["-m", str(model)])

        # Hardware acceleration handling
        if self.config.n_gpu_layers > 0 and shutil.which("nvidia-smi"):
            cmd.extend(["-ngl", str(self.config.n_gpu_layers)])

        cmd.extend(self.config.extra_args)

        logger.info("Starting embedded server daemon: %s", " ".join(cmd[:4]))
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as e:
            logger.error("Failed to spawn embedded server daemon: %s", e)
            return False

        if not self._registered_cleanup:
            atexit.register(self.stop)
            self._registered_cleanup = True

        # Polling healthcheck
        start_time = time.perf_counter()
        while (time.perf_counter() - start_time) < self.config.timeout_s:
            if self.is_healthy():
                logger.info(
                    "Embedded server verified healthy on port %d in %.2fs",
                    self.config.port,
                    time.perf_counter() - start_time,
                )
                return True
            time.sleep(0.5)

        logger.error(
            "Embedded server failed to respond within %.1fs timeout",
            self.config.timeout_s,
        )
        self.stop()
        return False

    def is_healthy(self) -> bool:
        """Polls the /v1/models endpoint."""
        url = f"http://{self.config.host}:{self.config.port}/v1/models"
        try:
            with httpx.Client(timeout=1.0) as client:
                res = client.get(url)
                return res.status_code == 200
        except Exception:
            return False

    def stop(self) -> None:
        """Gracefully terminates the background daemon."""
        if self.process:
            logger.info("Shutting down embedded server (PID %d)...", self.process.pid)
            try:
                self.process.terminate()
                self.process.wait(timeout=3.0)
            except Exception:
                with contextlib.suppress(Exception):
                    self.process.kill()
            self.process = None

    def get_client(self) -> Any:
        """Returns an OpenAI client bound to the embedded server endpoint."""
        try:
            from openai import OpenAI

            return OpenAI(
                base_url=f"http://{self.config.host}:{self.config.port}/v1",
                api_key="mock",
            )
        except ImportError as err:
            raise ImportError(
                "openai package required for client instantiation. Install via 'pip install openai'."
            ) from err


# Global singleton instance
_embedded_server_manager: EmbeddedServerManager | None = None


def bootstrap_embedded_server(
    config: EmbeddedServerConfig | None = None,
) -> EmbeddedServerManager:
    """Bootstraps and ensures the global embedded server is running."""
    global _embedded_server_manager
    if _embedded_server_manager is None:
        _embedded_server_manager = EmbeddedServerManager(config)
    _embedded_server_manager.start()
    return _embedded_server_manager


def shutdown_embedded_server() -> None:
    """Shuts down the global embedded server if active."""
    global _embedded_server_manager
    if _embedded_server_manager is not None:
        _embedded_server_manager.stop()
        _embedded_server_manager = None
