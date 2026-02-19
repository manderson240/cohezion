"""Token usage telemetry tracking for Cohezion."""

from __future__ import annotations

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
    _budget_usd: float = 5.0  # Default $5.0 session budget
    _total_spent: float = 0.0

    def __new__(cls, *args: Any, **kwargs: Any) -> TokenEfficiencyTracker:
        if cls._instance is None:
            cls._instance = super(TokenEfficiencyTracker, cls).__new__(cls)
        return cls._instance

    def __init__(self, budget: float = 5.0):
        if self._initialized:
            return
        self.records: list[TokenRecord] = []
        self._session_id = f"session_{int(time.time())}"
        self._budget_usd = budget
        self._total_spent = 0.0
        TokenEfficiencyTracker._initialized = True
        logger.info(
            f"TokenEfficiencyTracker initialized for session {self._session_id} with budget ${self._budget_usd}"
        )

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
        self._total_spent += cost

        if len(self.records) >= 10:
            self.persist_to_vault()

        return record

    def get_budget_status(self) -> dict[str, float | bool]:
        """Return the current budget usage status."""
        epsilon = 1e-6
        return {
            "budget_usd": self._budget_usd,
            "total_spent_usd": self._total_spent,
            "remaining_usd": max(0.0, self._budget_usd - self._total_spent),
            "usage_percent": (self._total_spent / self._budget_usd) * 100
            if self._budget_usd > 0
            else 0,
            "is_exhausted": self._total_spent >= (self._budget_usd - epsilon),
            "is_critical": self._total_spent >= (self._budget_usd * 0.9 - epsilon),
        }

    def persist_to_vault(self) -> None:
        """Persist collected records to the Vault via MCP."""
        try:
            mcp = get_mcp_client()
            path = f"telemetry/tokens/{self._session_id}.json"

            # Load existing if any
            data: dict[str, Any] = {"session_id": self._session_id, "records": [], "summary": {}}
            try:
                content = mcp.vault_read(path)
                loaded_data: Any = json.loads(content)
                if isinstance(loaded_data, dict):
                    data = loaded_data
            except Exception:
                pass

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
