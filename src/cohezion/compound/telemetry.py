"""Token usage telemetry tracking for Cohezion."""

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from cohezion.core.mcp_client import get_mcp_client

logger = logging.getLogger(__name__)


@dataclass
class TokenRecord:
    """Single LLM call token record."""

    timestamp: str
    model: str
    agent: str
    task_type: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float = 0.0
    session_id: str | None = None


class TokenEfficiencyTracker:
    """
    Singleton tracker for token usage across the swarm.
    Persists periodically to the Vault.
    """

    _instance: "TokenEfficiencyTracker | None" = None
    _initialized: bool = False
    _session_id: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TokenEfficiencyTracker, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.records: list[TokenRecord] = []
        self._session_id = f"session_{int(time.time())}"
        TokenEfficiencyTracker._initialized = True
        logger.info(f"TokenEfficiencyTracker initialized for session {self._session_id}")

    def record_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        agent: str = "unknown",
        task_type: str = "general",
        session_id: str | None = None,
    ) -> TokenRecord:
        """Record a single LLM call's token usage."""
        cost = 0.0
        total = max(0, input_tokens + output_tokens)

        lower_model = model.lower()
        if "pro" in lower_model or "premium" in lower_model:
            cost = (total / 1_000_000) * 10.0
        elif "flash" in lower_model or "economy" in lower_model:
            cost = (total / 1_000_000) * 0.1

        record = TokenRecord(
            timestamp=datetime.now().isoformat(),
            model=model,
            agent=agent,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
            cost_usd=cost,
            session_id=session_id or self._session_id,
        )
        self.records.append(record)

        if len(self.records) >= 10:
            self.persist_to_vault()

        return record

    def persist_to_vault(self):
        """Persist collected records to the Vault via MCP."""
        try:
            mcp = get_mcp_client()
            path = f"telemetry/tokens/{self._session_id}.json"

            data: dict[str, Any]
            try:
                content = mcp.vault_read(path)
                data = json.loads(content)
                if not isinstance(data, dict):
                    data = {"session_id": self._session_id, "records": [], "summary": {}}
            except Exception:
                data = {"session_id": self._session_id, "records": [], "summary": {}}

            records_list = data.get("records")
            if not isinstance(records_list, list):
                records_list = []
                data["records"] = records_list

            records_list.extend([asdict(r) for r in self.records])
            self.records = []

            total_tokens = sum(float(r.get("total_tokens", 0)) for r in records_list)
            total_cost = sum(float(r.get("cost_usd", 0.0)) for r in records_list)
            data["summary"] = {
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost,
                "last_updated": datetime.now().isoformat(),
                "call_count": len(records_list),
            }

            mcp.vault_write(path, json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to persist telemetry: {e}")


def get_tracker() -> TokenEfficiencyTracker:
    return TokenEfficiencyTracker()
