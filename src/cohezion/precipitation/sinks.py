"""PrecipitationEvent sinks — vault, SurrealDB, and git ledger.

Every sink implements the same minimal protocol:
    async def write(event: PrecipitationEvent) -> None

Sinks are registered on the bus; the drainer catches any exception they raise so a
misconfigured sink (e.g., SurrealDB down) cannot wedge the precipitation stream.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any

from .events import PrecipitationEvent, PrecipitationKind


logger = logging.getLogger(__name__)


def _default_vault_dir() -> Path:
    """Resolve the vault directory at call time so tests can monkeypatch the env."""
    return Path(os.environ.get("COHEZION_VAULT_DIR", str(Path.home() / "vaults/cohezion-vault")))


# Preserved for backwards-compatible imports; prefer _default_vault_dir() in new code.
DEFAULT_VAULT_DIR = _default_vault_dir()

# Kinds that deserve their own git-tracked ledger entry.
_GIT_LEDGER_KINDS: frozenset[PrecipitationKind] = frozenset(
    {
        PrecipitationKind.TRAINING_CHECKPOINT,
        PrecipitationKind.GENERATION_SPAWN,
        PrecipitationKind.WITNESS_MARK,
        PrecipitationKind.CONSENSUS_RATIFIED,
    }
)


class VaultSink:
    """Append-only JSONL sink under the cohezion-vault.

    One file per UTC day: `precipitation/events-YYYY-MM-DD.jsonl`.
    Directly writes files (no MCP dependency) so it works in tests and offline.
    """

    def __init__(self, vault_dir: Path | None = None) -> None:
        self.vault_dir = Path(vault_dir) if vault_dir else _default_vault_dir()
        self.events_dir = self.vault_dir / "precipitation"
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = asyncio.Lock()

    def _path_for(self, event: PrecipitationEvent) -> Path:
        day = event.timestamp_valid.date()
        return self.events_dir / f"events-{day.isoformat()}.jsonl"

    async def write(self, event: PrecipitationEvent) -> None:
        path = self._path_for(event)
        line = json.dumps(event.to_dict(), separators=(",", ":")) + "\n"
        async with self._write_lock:
            # File IO remains sync inside the lock; the lock prevents interleaving.
            # For the expected event rate (<<1k/s), this is faster than shelling to aiofiles.
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)

    @classmethod
    def iter_events(cls, day: date, vault_dir: Path | None = None) -> list[dict[str, Any]]:
        """Read back all events for a given UTC day. Used by orchestrator + tests."""
        base = Path(vault_dir) if vault_dir else _default_vault_dir()
        path = base / "precipitation" / f"events-{day.isoformat()}.jsonl"
        if not path.exists():
            return []
        out: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out


class SurrealSink:
    """HTTP-based SurrealDB sink.

    Uses the SurrealDB HTTP /sql endpoint directly rather than the ws-based
    `surrealdb` python client, because this project runs SurrealDB on HTTP :8001.
    Failures are logged and swallowed — precipitation never blocks on a DB.
    """

    def __init__(
        self,
        url: str | None = None,
        namespace: str = "cohezion",
        database: str = "main",
        username: str = "root",
        password: str = "root",
        table: str = "precipitation_event",
    ) -> None:
        self.url = url or os.environ.get("COHEZION_SURREAL_URL", "http://127.0.0.1:8001")
        self.namespace = namespace
        self.database = database
        self.username = username
        self.password = password
        self.table = table
        self._client: Any = None  # lazily imported httpx.AsyncClient

    async def _get_client(self) -> Any:
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(timeout=5.0)
        return self._client

    async def write(self, event: PrecipitationEvent) -> None:
        try:
            client = await self._get_client()
            payload = _surreal_insert_stmt(self.table, event)
            response = await client.post(
                f"{self.url}/sql",
                content=payload,
                headers={
                    "Content-Type": "text/plain",
                    "Accept": "application/json",
                    "Surreal-NS": self.namespace,
                    "Surreal-DB": self.database,
                },
                auth=(self.username, self.password),
            )
            if response.status_code >= 400:
                logger.warning(
                    "SurrealSink HTTP %d for event_id=%s: %s",
                    response.status_code,
                    event.event_id,
                    response.text[:200],
                )
                return
            # SurrealDB returns 200 even when individual statements fail.
            try:
                body = response.json()
            except ValueError:
                return
            if isinstance(body, list):
                for statement in body:
                    if isinstance(statement, dict) and statement.get("status") == "ERR":
                        logger.warning(
                            "SurrealSink statement ERR for event_id=%s: %s",
                            event.event_id,
                            str(statement.get("result"))[:300],
                        )
        except Exception as exc:
            logger.warning(
                "SurrealSink dropped event_id=%s: %s",
                event.event_id,
                exc,
            )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


class GitLedgerSink:
    """Append significant events to a git-trackable JSONL ledger.

    We don't auto-commit here — Phase 9 and human-in-the-loop commits do that.
    This sink only writes data/precipitation/ledger.jsonl so it can be batched.
    """

    def __init__(self, ledger_path: Path | str = "data/precipitation/ledger.jsonl") -> None:
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = asyncio.Lock()

    async def write(self, event: PrecipitationEvent) -> None:
        if event.kind not in _GIT_LEDGER_KINDS:
            return
        line = json.dumps(event.to_dict(), separators=(",", ":")) + "\n"
        async with self._write_lock:
            with self.ledger_path.open("a", encoding="utf-8") as fh:
                fh.write(line)


def _surreal_insert_stmt(table: str, event: PrecipitationEvent) -> str:
    """Render a CREATE ... CONTENT statement for SurrealDB.

    SurrealDB quirks handled here:
    1. It does not auto-coerce JSON strings into its datetime type — we inject
       `type::datetime("...")` casts for valid_from / transaction_time.
    2. Fields of type `option<T>` reject JSON `null` — it's a distinct value
       from NONE. We drop any top-level None-valued keys before serialization.

    The datetime field names are stable and controlled by us, so the string
    replacement is safe.
    """
    data = {k: v for k, v in event.to_dict().items() if v is not None}
    body = json.dumps(data, separators=(",", ":"))
    for field_name in ("valid_from", "transaction_time"):
        placeholder_start = f'"{field_name}":"'
        idx = body.find(placeholder_start)
        if idx < 0:
            continue
        start_value = idx + len(placeholder_start)
        end_value = body.find('"', start_value)
        iso_value = body[start_value:end_value]
        replacement = f'"{field_name}":type::datetime("{iso_value}")'
        body = body[:idx] + replacement + body[end_value + 1 :]
    return f"CREATE {table} CONTENT {body};"


def register_default_sinks(bus: Any, *, enable_surreal: bool = True) -> dict[str, Any]:
    """Attach Vault + Git + optionally Surreal sinks to the bus.

    Returns a dict of sinks so the caller can close() them at shutdown.
    """

    vault = VaultSink()
    git = GitLedgerSink()
    sinks: dict[str, Any] = {"vault": vault, "git": git}

    bus.subscribe(vault.write, kind=None)
    bus.subscribe(git.write, kind=None)

    if enable_surreal:
        surreal = SurrealSink()
        sinks["surreal"] = surreal
        bus.subscribe(surreal.write, kind=None)

    return sinks


__all__ = [
    "DEFAULT_VAULT_DIR",
    "GitLedgerSink",
    "SurrealSink",
    "VaultSink",
    "register_default_sinks",
]
