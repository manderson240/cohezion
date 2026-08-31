"""Delegation / escalation logger for inference tier transitions.

Persists every Tier-1 → Tier-2 escalation to the ``delegation_log`` table in
SurrealDB and publishes an ``AGENT_COMPLETE`` event to the global EventBus so
downstream monitoring tools can react in real time.

Usage
-----
>>> logger = DelegationLogger()
>>> await logger.log_escalation(
...     task_class="reasoning",
...     from_tier=1,
...     to_tier=2,
...     evi_score=0.62,
...     reason="lemonade_unhealthy",
... )
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

from cohezion.core.event_bus import Event, EventBus, get_event_bus
from cohezion.reliability import get_circuit

_log = logging.getLogger(__name__)

# EVI threshold below which we do NOT emit escalation records (noise suppression)
EVI_ESCALATION_THRESHOLD: float = 0.75

# SurrealDB HTTP API base — default local dev, overridable via env
_SURREAL_URL: str = os.environ.get("SURREAL_HTTP_URL", "http://localhost:8001")
_SURREAL_NS: str = os.environ.get("SURREAL_NS", "cohezion")
_SURREAL_DB: str = os.environ.get("SURREAL_DB", "cohezion")
_SURREAL_USER: str = os.environ.get("SURREAL_USER", "admin")
_SURREAL_PASS: str = os.environ.get("SURREAL_PASSWORD", "root")

_SQL_TEMPLATE = (
    "CREATE delegation_log CONTENT {{"
    '"task_class": "{task_class}", '
    '"from_tier": {from_tier}, '
    '"to_tier": {to_tier}, '
    '"evi_score": {evi_score}, '
    '"reason": "{reason}", '
    '"ts": time::now()'
    "}}"
)


@dataclass
class EscalationRecord:
    """A single escalation event persisted to SurrealDB.

    Parameters
    ----------
    task_class : str
        Task classification label (e.g. ``"reasoning"``).
    from_tier : int
        Origin routing tier (1 = Lemonade local, 0 = pre-flight).
    to_tier : int
        Destination routing tier (2 = Ollama cloud).
    evi_score : float
        Estimated Value of Inference score at decision time.
    reason : str
        Short machine-readable reason code (e.g. ``"lemonade_unhealthy"``).
    ts : float
        Unix timestamp of the escalation (auto-set to ``time.time()``).
    """

    task_class: str
    from_tier: int
    to_tier: int
    evi_score: float
    reason: str
    ts: float = 0.0

    def __post_init__(self) -> None:
        if self.ts == 0.0:
            self.ts = time.time()


class DelegationLogger:
    """Logs inference delegation / escalation events to SurrealDB + EventBus.

    Parameters
    ----------
    surreal_url : str
        SurrealDB HTTP API base URL.  Defaults to ``http://localhost:8001``.
    surreal_ns : str
        SurrealDB namespace.  Defaults to ``"cohezion"``.
    surreal_db : str
        SurrealDB database.  Defaults to ``"cohezion"``.
    surreal_user : str
        SurrealDB username.
    surreal_pass : str
        SurrealDB password.
    http_timeout : float
        Timeout in seconds for SurrealDB HTTP calls.
    """

    def __init__(
        self,
        surreal_url: str = _SURREAL_URL,
        surreal_ns: str = _SURREAL_NS,
        surreal_db: str = _SURREAL_DB,
        surreal_user: str = _SURREAL_USER,
        surreal_pass: str = _SURREAL_PASS,
        http_timeout: float = 5.0,
    ) -> None:
        self._surreal_url = surreal_url.rstrip("/")
        self._surreal_ns = surreal_ns
        self._surreal_db = surreal_db
        self._surreal_user = surreal_user
        self._surreal_pass = surreal_pass
        self._http_timeout = http_timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def log_escalation(
        self,
        task_class: str,
        from_tier: int,
        to_tier: int,
        evi_score: float,
        reason: str,
    ) -> bool:
        """Persist an escalation event and publish an EventBus notification.

        Escalations with ``evi_score < EVI_ESCALATION_THRESHOLD`` are silently
        dropped — these represent cases where the local model was already
        expected to fail, so escalation is expected and not worth recording.

        Parameters
        ----------
        task_class : str
            Task classification label (e.g. ``"reasoning"``).
        from_tier : int
            Origin routing tier.
        to_tier : int
            Destination routing tier.
        evi_score : float
            Estimated Value of Inference score (0-1).
        reason : str
            Short machine-readable reason code.

        Returns
        -------
        bool
            ``True`` if the escalation was persisted successfully, ``False``
            if it was gated out by the EVI threshold or if persistence failed
            (the EventBus publish still fires regardless).
        """
        if evi_score < EVI_ESCALATION_THRESHOLD:
            _log.debug(
                "DelegationLogger: EVI %.3f < %.3f — escalation not recorded (expected)",
                evi_score,
                EVI_ESCALATION_THRESHOLD,
            )
            return False

        record = EscalationRecord(
            task_class=task_class,
            from_tier=from_tier,
            to_tier=to_tier,
            evi_score=evi_score,
            reason=reason,
        )

        persisted = await self._persist_to_surreal(record)
        await self._publish_event(record)
        return persisted

    # ------------------------------------------------------------------
    # Internal: SurrealDB HTTP persistence
    # ------------------------------------------------------------------

    async def _persist_to_surreal(self, record: EscalationRecord) -> bool:
        """Write the escalation record to SurrealDB via the HTTP SQL API.

        Uses a named circuit breaker ``"delegation_logger_surreal"`` so that
        repeated SurrealDB outages trip the breaker and stop hammering the
        endpoint.

        Parameters
        ----------
        record : EscalationRecord
            The escalation event to persist.

        Returns
        -------
        bool
            ``True`` on success, ``False`` on failure or open circuit.
        """
        circuit = get_circuit(
            "delegation_logger_surreal",
            failure_threshold=3,
            recovery_timeout=30.0,
        )
        if not circuit.allow_request():
            _log.warning(
                "DelegationLogger: circuit open — SurrealDB write skipped for task=%s",
                record.task_class,
            )
            return False

        sql = (
            "CREATE delegation_log CONTENT {"
            f'"task_class": "{record.task_class}", '
            f'"from_tier": {record.from_tier}, '
            f'"to_tier": {record.to_tier}, '
            f'"evi_score": {record.evi_score:.6f}, '
            f'"reason": "{record.reason}", '
            f'"ts": "{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.ts))}"'
            "}"
        )
        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                resp = await client.post(
                    f"{self._surreal_url}/sql",
                    content=sql,
                    headers={
                        "Content-Type": "application/json",
                        "NS": self._surreal_ns,
                        "DB": self._surreal_db,
                        "Accept": "application/json",
                    },
                    auth=(self._surreal_user, self._surreal_pass),
                )
                resp.raise_for_status()
                circuit.record_success()
                _log.info(
                    "DelegationLogger: escalation persisted task=%s tier%d->tier%d evi=%.3f",
                    record.task_class,
                    record.from_tier,
                    record.to_tier,
                    record.evi_score,
                )
                return True
        except httpx.HTTPStatusError as exc:
            circuit.record_failure()
            _log.error(
                "DelegationLogger: SurrealDB HTTP error %s: %s",
                exc.response.status_code,
                exc,
            )
            return False
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            circuit.record_failure()
            _log.error("DelegationLogger: SurrealDB connection/timeout error: %s", exc)
            return False
        except Exception as exc:
            circuit.record_failure()
            _log.error("DelegationLogger: unexpected SurrealDB error: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal: EventBus publication
    # ------------------------------------------------------------------

    async def _publish_event(self, record: EscalationRecord) -> None:
        """Publish an ``AGENT_COMPLETE`` event to the global EventBus.

        Parameters
        ----------
        record : EscalationRecord
            The escalation event that was recorded.
        """
        try:
            bus: EventBus = await get_event_bus()
            event = Event.agent_complete(
                agent_name="DelegationLogger",
                result="escalation",
                duration_ms=0.0,
                task_class=record.task_class,
                from_tier=record.from_tier,
                to_tier=record.to_tier,
                evi_score=record.evi_score,
                reason=record.reason,
            )
            await bus.publish(event)
            _log.debug(
                "DelegationLogger: EventBus event published for task=%s",
                record.task_class,
            )
        except Exception as exc:
            _log.warning("DelegationLogger: EventBus publish failed (non-critical): %s", exc)
