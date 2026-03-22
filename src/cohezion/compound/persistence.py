"""Compound cycle persistence -- SurrealDB with JSONL fallback."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from cohezion.core.mcp_client import get_mcp_client


logger = logging.getLogger(__name__)

_JSONL_DIR = Path("data/compound/cycles")


class CompoundPersistence:
    """Persist compound cycle results to SurrealDB or JSONL.

    Parameters
    ----------
    jsonl_dir : Path | None
        Override directory for JSONL fallback files.
    """

    def __init__(self, jsonl_dir: Path | None = None) -> None:
        self._jsonl_dir = jsonl_dir or _JSONL_DIR
        self._surreal_available: bool | None = None

    async def save_cycle(self, skill_name: str, cycle_data: dict[str, Any]) -> str:
        """Save a cycle result.

        Parameters
        ----------
        skill_name : str
            PRIME skill name.
        cycle_data : dict[str, Any]
            Serialized cycle result.

        Returns
        -------
        str
            Record ID (SurrealDB) or JSONL reference.
        """
        # Tier 1: Vault (Structured & Contextual)
        try:
            return await self._save_to_vault(skill_name, cycle_data)
        except Exception as e:
            logger.debug(f"Vault save failed: {e}")

        # Tier 2: SurrealDB (Fast Query & Physics Vectors)
        if await self._check_surreal():
            try:
                return await self._save_to_surreal(skill_name, cycle_data)
            except Exception:
                logger.warning("SurrealDB save failed, falling back to JSONL")

        # Tier 3: JSONL (Local Fallback)
        return self._save_to_jsonl(skill_name, cycle_data)

    async def load_history(self, skill_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Load cycle history for a skill.

        Parameters
        ----------
        skill_name : str
            PRIME skill name.
        limit : int
            Maximum records to return.

        Returns
        -------
        list[dict[str, Any]]
            Most recent cycle records first.
        """
        # Tier 1: Vault
        try:
            history = await self._load_from_vault(skill_name, limit)
            if history:
                return history
        except Exception as e:
            logger.debug(f"Vault load failed: {e}")

        # Tier 2: SurrealDB
        if await self._check_surreal():
            try:
                return await self._load_from_surreal(skill_name, limit)
            except Exception:
                logger.warning("SurrealDB load failed, falling back to JSONL")

        # Tier 3: JSONL
        return self._load_from_jsonl(skill_name, limit)

    async def _check_surreal(self) -> bool:
        """Check if SurrealDB is available (cached)."""
        if self._surreal_available is None:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get("http://localhost:8000/health")
                    self._surreal_available = resp.status_code == 200
            except Exception:
                self._surreal_available = False
        return self._surreal_available

    async def _save_to_surreal(self, skill_name: str, cycle_data: dict[str, Any]) -> str:
        """Save to SurrealDB compound_cycle table."""
        from cohezion.persistence.surreal_client import get_client

        client = await get_client()
        record = {"skill_name": skill_name, **cycle_data}
        result = await client.create("compound_cycle", record)
        record_id = result[0]["id"] if isinstance(result, list) and result else "unknown"
        return str(record_id)

    async def _load_from_surreal(self, skill_name: str, limit: int) -> list[dict[str, Any]]:
        """Load from SurrealDB."""
        from cohezion.persistence.surreal_client import get_client

        client = await get_client()
        result = await client.query(
            "SELECT * FROM compound_cycle WHERE skill_name = $name ORDER BY timestamp DESC LIMIT $limit",
            {"name": skill_name, "limit": limit},
        )
        if isinstance(result, list):
            return result[:limit]
        return []

    async def _save_to_vault(self, skill_name: str, cycle_data: dict[str, Any]) -> str:
        """Save cycle result to Vault."""
        mcp = get_mcp_client()
        safe_name = skill_name.replace("/", "_").replace(" ", "_").lower()
        import time

        timestamp = int(time.time())
        path = f"cycles/{safe_name}/{timestamp}.json"
        mcp.vault_write(path, json.dumps(cycle_data, indent=2))
        logger.debug(f"Cycle saved to Vault: {path}")
        return f"vault:{path}"

    async def _load_from_vault(
        self, skill_name: str, limit: int
    ) -> list[dict[str, Any]]:
        """Load cycle history from Vault."""
        mcp = get_mcp_client()
        safe_name = skill_name.replace("/", "_").replace(" ", "_").lower()
        folder = f"cycles/{safe_name}"
        try:
            files = mcp.vault_list(folder)
            # Sort files descending to get latest
            files.sort(reverse=True)
            records = []
            for filepath in files[:limit]:
                content = mcp.vault_read(filepath)
                records.append(json.loads(content))
            return records
        except Exception:
            return []

    def _save_to_jsonl(self, skill_name: str, cycle_data: dict[str, Any]) -> str:
        """Save to JSONL file as fallback."""
        import time

        self._jsonl_dir.mkdir(parents=True, exist_ok=True)
        safe_name = skill_name.replace("/", "_").replace(" ", "_").lower()
        path = self._jsonl_dir / f"{safe_name}.jsonl"
        record = {"skill_name": skill_name, "timestamp": time.time(), **cycle_data}
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return f"jsonl:{safe_name}:{record['timestamp']}"

    def _load_from_jsonl(self, skill_name: str, limit: int) -> list[dict[str, Any]]:
        """Load from JSONL file."""
        safe_name = skill_name.replace("/", "_").replace(" ", "_").lower()
        path = self._jsonl_dir / f"{safe_name}.jsonl"
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8").strip().splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        # Return most recent first
        records.reverse()
        return records[:limit]
