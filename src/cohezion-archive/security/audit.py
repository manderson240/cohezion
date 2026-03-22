"""
Audit Logger - Structured logging for security events.

Provides:
- JSON Lines format for analysis
- API request logging
- Security event logging
- Log rotation support
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

AUDIT_LOG_DIR = Path(os.environ.get("COHEZION_LOG_DIR", "logs"))
AUDIT_LOG_FILE = AUDIT_LOG_DIR / "audit.jsonl"


@dataclass
class AuditEvent:
    """Structured audit event."""

    timestamp: str
    event_type: str  # request, auth, security, error
    action: str
    user: str | None
    ip_address: str | None
    endpoint: str | None
    status: str
    details: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class AuditLogger:
    """
    Audit logger for security and compliance.

    Logs events in JSON Lines format for easy analysis.
    """

    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or AUDIT_LOG_DIR
        self.log_file = self.log_dir / "audit.jsonl"
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        """Create log directory if needed."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _write(self, event: AuditEvent) -> None:
        """Write event to log file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(event.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def log_request(
        self,
        endpoint: str,
        method: str,
        ip_address: str | None,
        user: str | None,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """Log an API request."""
        event = AuditEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_type="request",
            action=f"{method} {endpoint}",
            user=user,
            ip_address=ip_address,
            endpoint=endpoint,
            status="success" if status_code < 400 else "error",
            details={
                "method": method,
                "status_code": status_code,
                "latency_ms": latency_ms,
            },
        )
        self._write(event)

    def log_auth(
        self,
        action: str,
        user: str | None,
        ip_address: str | None,
        success: bool,
        reason: str = "",
    ) -> None:
        """Log an authentication event."""
        event = AuditEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_type="auth",
            action=action,
            user=user,
            ip_address=ip_address,
            endpoint=None,
            status="success" if success else "failure",
            details={"reason": reason},
        )
        self._write(event)

        if not success:
            logger.warning(f"Auth failure: {action} from {ip_address}")

    def log_security(
        self,
        action: str,
        threat_level: str,
        ip_address: str | None,
        details: dict[str, Any],
    ) -> None:
        """Log a security event."""
        event = AuditEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_type="security",
            action=action,
            user=None,
            ip_address=ip_address,
            endpoint=None,
            status=threat_level,
            details=details,
        )
        self._write(event)

        if threat_level in ("malicious", "blocked"):
            logger.warning(f"Security event: {action} - {details}")

    def log_debate(
        self,
        query_hash: str,
        model_chain: list[str],
        confidence: float,
        latency_ms: float,
    ) -> None:
        """Log a swarm debate execution."""
        event = AuditEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_type="debate",
            action="run_debate",
            user=None,
            ip_address=None,
            endpoint="/swarm/debate",
            status="success",
            details={
                "query_hash": query_hash,
                "model_chain": model_chain,
                "confidence": confidence,
                "latency_ms": latency_ms,
            },
        )
        self._write(event)

    def get_recent_events(self, limit: int = 100, event_type: str | None = None) -> list[dict]:
        """Read recent audit events."""
        if not self.log_file.exists():
            return []

        events = []
        with open(self.log_file) as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event_type is None or event.get("event_type") == event_type:
                        events.append(event)
                except json.JSONDecodeError:
                    continue

        return events[-limit:]


# Singleton
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
