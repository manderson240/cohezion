"""Unified logging to vault for all MCP servers."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path


# Vault log path
VAULT_LOG_PATH = Path(os.getenv("VAULT_LOG_PATH", "cloud-vault-mcp/vault/logs"))


class VaultLogHandler(logging.Handler):
    """Handler that writes logs to vault."""

    def __init__(self, server_name: str, level: int = logging.INFO):
        super().__init__(level)
        self.server_name = server_name
        self.log_file = VAULT_LOG_PATH / f"{server_name}.log"

        # Ensure directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, record: logging.LogRecord) -> None:
        """Emit log record to vault."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "server": self.server_name,
            "level": record.levelname,
            "message": self.format(record),
            "source": f"{record.filename}:{record.lineno}",
        }

        # Append to log file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")


class VaultLogger:
    """Logger that writes to both console and vault."""

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(f"mcp.{name}")
        self.logger.setLevel(level)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_format = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # Vault handler
        vault_handler = VaultLogHandler(name, level)
        vault_format = logging.Formatter("%(message)s")
        vault_handler.setFormatter(vault_format)
        self.logger.addHandler(vault_handler)

    def debug(self, msg: str, *args, **kwargs) -> None:
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self.logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        self.logger.exception(msg, *args, **kwargs)


# Cache of loggers
_loggers: dict[str, VaultLogger] = {}


def get_logger(name: str) -> VaultLogger:
    """Get or create vault logger."""
    if name not in _loggers:
        _loggers[name] = VaultLogger(name)
    return _loggers[name]
