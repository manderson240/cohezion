"""TokenLedger — make the Quarter-on-a-String Protocol MEASURABLE.

Extends the existing session token machinery rather than duplicating it:

  - ``cohezion.inference.token_budget.TokenUsageRecord`` already aggregates a
    process-lifetime view (``local_tokens``, ``cloud_cost_usd``,
    ``cloud_savings_usd``) and is wired into ``compound.local_inference`` (every
    execute_fn call does ``record.add_local`` / ``record.add_cloud``). The
    ``GlobalMetricsAggregator`` rolls per-skill ``total_tokens`` up for the API.

  - What was MISSING: a per-task ledger that (a) keeps an auditable row per task,
    (b) names the cost-avoided ("quarters saved") explicitly, and (c) is HONEST
    about the leak — ORCHESTRATION cloud spend (Claude subagents / main loop) is
    tracked as ``cloud_tokens`` so ``local_fraction`` is never a vanity 1.0 while
    we still pay cloud tokens to drive the loop.

The cloud rate constant (the "quarter" each local token saves) is the SAME blended
rate ``TokenUsageRecord.add_local`` uses — imported, not re-guessed.

Rows persist to a SurrealDB ``token_ledger`` table via the parameterized
``_surql_set`` builder imported from ``prompt_version_registry`` (injection-safe by
construction). Persistence is fail-open and OFF by default (the daemon enables it);
the table being absent never raises.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from cohezion.compound.prompt_version_registry import _surql_set
from cohezion.inference.token_budget import (
    _CLOUD_INPUT_PER_TOKEN,
    _CLOUD_OUTPUT_PER_TOKEN,
    TokenUsageRecord,
)


logger = logging.getLogger(__name__)

# The blended cloud rate one local token AVOIDS — identical to the average used by
# TokenUsageRecord.add_local. This is the "quarter" on the string.
_CLOUD_RATE_PER_TOKEN: float = (_CLOUD_INPUT_PER_TOKEN + _CLOUD_OUTPUT_PER_TOKEN) / 2

_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
}


@dataclass
class LedgerRow:
    """One auditable accounting line."""

    task: str
    local_tokens: int
    cloud_tokens: int
    cached_hits: int
    cost_avoided_usd: float
    cloud_cost_usd: float
    ts: float


@dataclass
class LedgerSummary:
    """Cumulative Quarter-on-a-String view.

    ``local_fraction`` is the honesty metric: < 1.0 whenever cloud orchestration
    tokens were spent, so a real leak can never hide behind an all-$0 headline.
    """

    local_tokens: int
    cloud_tokens: int
    cached_hits: int
    quarters_saved_usd: float
    cloud_cost_usd: float
    local_fraction: float


class TokenLedger:
    """Per-task local-vs-cloud token ledger with cost-avoided ("quarters saved").

    Wraps a :class:`TokenUsageRecord` for the cumulative spine and keeps an
    explicit row per task for auditability.
    """

    def __init__(self, *, persist: bool = False) -> None:
        self._rows: list[LedgerRow] = []
        self._record = TokenUsageRecord()
        self._cached_hits = 0
        self._persist = persist

    def record_local(self, task: str, tokens: int, *, cached_hits: int = 0) -> LedgerRow:
        """Record tokens handled FREE on local silicon (NPU/iGPU/CPU).

        Accrues cost-avoided (the quarter saved) and leaves cloud columns at zero.
        """
        self._record.add_local(tokens)
        cost_avoided = tokens * _CLOUD_RATE_PER_TOKEN
        self._cached_hits += cached_hits
        row = LedgerRow(
            task=task,
            local_tokens=int(tokens),
            cloud_tokens=0,
            cached_hits=int(cached_hits),
            cost_avoided_usd=cost_avoided,
            cloud_cost_usd=0.0,
            ts=time.time(),
        )
        self._rows.append(row)
        self._persist_row(row)
        return row

    def record_cloud(self, task: str, tokens: int) -> LedgerRow:
        """Record ORCHESTRATION cloud spend (Claude subagents / main loop) — REAL $.

        No cost is "avoided" here; this is the leak the metric must expose. Split is
        unknown at this layer, so the blended rate is applied to the whole count.
        """
        cost = tokens * _CLOUD_RATE_PER_TOKEN
        self._record.cloud_cost_usd += cost
        row = LedgerRow(
            task=task,
            local_tokens=0,
            cloud_tokens=int(tokens),
            cached_hits=0,
            cost_avoided_usd=0.0,
            cloud_cost_usd=cost,
            ts=time.time(),
        )
        self._rows.append(row)
        self._persist_row(row)
        return row

    def summary(self) -> LedgerSummary:
        """Cumulative {local, cloud, quarters_saved_usd, local_fraction}."""
        local = sum(r.local_tokens for r in self._rows)
        cloud = sum(r.cloud_tokens for r in self._rows)
        denom = local + cloud
        return LedgerSummary(
            local_tokens=local,
            cloud_tokens=cloud,
            cached_hits=self._cached_hits,
            quarters_saved_usd=round(sum(r.cost_avoided_usd for r in self._rows), 6),
            cloud_cost_usd=round(sum(r.cloud_cost_usd for r in self._rows), 6),
            local_fraction=(local / denom) if denom > 0 else 0.0,
        )

    @property
    def rows(self) -> list[LedgerRow]:
        return list(self._rows)

    def _persist_row(self, row: LedgerRow) -> None:
        """Write one row to SurrealDB ``token_ledger`` (fail-open, table-absent tolerant).

        Every value goes through the imported ``_surql_set`` (json.dumps-inert) — no
        hand-built interpolated f-string, so the row inherits the injection-safe path.
        """
        if not self._persist:
            return
        try:
            import httpx

            query = "CREATE token_ledger SET " + _surql_set(
                {
                    "task": row.task,
                    "local_tokens": row.local_tokens,
                    "cloud_tokens": row.cloud_tokens,
                    "cached_hits": row.cached_hits,
                    "cost_avoided_usd": row.cost_avoided_usd,
                    "cloud_cost_usd": row.cloud_cost_usd,
                    "ts": row.ts,
                }
            )
            httpx.post(
                _SURREAL_URL,
                content=query,
                headers=_SURREAL_HEADERS,
                auth=("root", "root"),
                timeout=3.0,
            )
        except Exception as exc:  # fail-open: ledger never blocks execution
            logger.debug("token_ledger persist skipped: %s", exc)
