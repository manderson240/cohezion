"""Claim-based consumer for the datamesh event backbone — the missing subscriber.

2026-07-10: the datamesh EventBus dead-ended — DataMeshEventBridge persists every
event to SurrealDB ``data_product_event`` and NOTHING ever consumed them (research
daemon diagnosis §3). SurrealDB-native LIVE queries were probed and are
**unsupported on this deployment** (3.1.5, versioned SurrealKV → HTTP reports
``LiveQueryNotSupported``; the WS generator yields nothing). So eventing here is
honest at-least-once polling with idempotent claims — the same pattern the harness
trusts for the session bus (SCP1: atomic ``array::add`` set-insert claims, never
SELECT-then-write; record-id charset guard on every raw interpolation).

Flow (proactive agentic SurrealDB + local inference):

    DataMeshEventBridge.publish → data_product_event (durable)
    EventConsumer.run_once      → fetch unclaimed → claim (array::add, idempotent)
                                → deterministic route by event_type
                                → actionable events become work-queue items whose
                                  title/description are summarized by LOCAL
                                  inference (:13305, $0) with a raw-payload
                                  fallback — inference assists, rules decide.

Claim-before-handle gives exactly-once handling per consumer id (SCP4 pattern);
a handler crash after claim drops that one event for this consumer — acceptable
for triage, and the failure is counted honestly in the run summary.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from collections.abc import Callable
from typing import Any


logger = logging.getLogger(__name__)

SURREAL_URL = "http://127.0.0.1:8001/sql"
_HEADERS = {"surreal-ns": "cohezion", "surreal-db": "main", "Content-Type": "text/plain"}
_AUTH = "Basic cm9vdDpyb290"  # root:root — fleet default, matches compound_persist
WORK_QUEUE_API = "http://localhost:8080/api/work-queue"
TABLE = "data_product_event"
DEFAULT_CONSUMER_ID = "datamesh-event-consumer"

# SCP1: record ids are raw-interpolated into SurrealQL — guard the charset.
_SAFE_RECORD_ID = re.compile(r"^[A-Za-z0-9_]+:[A-Za-z0-9⟨⟩_-]+$")

# Deterministic routing table (ponytail: a rule suffices for WHICH events act;
# local inference only writes the human-facing summary).
ACTIONABLE_EVENT_TYPES = {
    "data_product_quality_alert",
    "domain_health_degraded",
}
TALLY_ONLY_EVENT_TYPES = {
    "data_product_created",
    "data_product_updated",
    "lineage_updated",
    "custom",
}


def _default_sql(query: str, timeout: float = 10.0) -> list[dict[str, Any]]:
    req = urllib.request.Request(
        SURREAL_URL,
        data=query.encode(),
        headers={**_HEADERS, "Authorization": _AUTH},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed localhost literal
        return json.loads(resp.read())


def _default_summarize(event_type: str, payload: str) -> str:
    """One bounded local-inference call ($0); raw-slice fallback on any failure."""
    try:
        # F0/F1 lesson (learned the hard way TWICE today): OMIT temperature so the
        # loaded card's sampling applies — temp=0.0 on Gemma-family cards yields
        # degenerate empty output (finish_reason=length, content=''). Generous
        # max_tokens per the local-inference budget memory ($0 local).
        body = {
            "model": "Gemma-4-E4B-it-GGUF",
            "max_tokens": 512,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Summarize this {event_type} event in ONE sentence for an "
                        f"engineering kanban card (plain text, no preamble): {payload[:1200]}"
                    ),
                }
            ],
        }
        req = urllib.request.Request(
            "http://localhost:13305/api/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60.0) as resp:  # noqa: S310 — fixed localhost literal
            out = json.loads(resp.read())
        text = str(out["choices"][0]["message"]["content"]).strip()
        if text:
            return text[:400]
    except Exception as exc:
        logger.debug("event summarize fell back to raw payload: %s", exc)
    return payload[:400]


def _default_file_work_item(title: str, description: str, domain: str) -> str:
    body = json.dumps(
        {
            "type": "improvement",
            "title": title[:180],
            "description": description[:1500],
            "relevance": "APPLY",
            "domain": domain,
            "notes": "auto-filed by datamesh EventConsumer",
        }
    ).encode()
    req = urllib.request.Request(
        WORK_QUEUE_API,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15.0) as resp:  # noqa: S310 — fixed localhost literal
        return str(json.loads(resp.read()).get("id", "?"))


class EventConsumer:
    """Drains ``data_product_event`` with idempotent per-consumer claims."""

    def __init__(
        self,
        consumer_id: str = DEFAULT_CONSUMER_ID,
        *,
        sql_fn: Callable[[str], list[dict[str, Any]]] | None = None,
        summarize_fn: Callable[[str, str], str] | None = None,
        file_work_item_fn: Callable[[str, str, str], str] | None = None,
    ) -> None:
        if not re.match(r"^[A-Za-z0-9_.\-]+$", consumer_id):
            raise ValueError(f"unsafe consumer_id: {consumer_id!r}")
        self.consumer_id = consumer_id
        self._sql = sql_fn or _default_sql
        self._summarize = summarize_fn or _default_summarize
        self._file_work_item = file_work_item_fn or _default_file_work_item
        self._ensure_claim_field()

    def _ensure_claim_field(self) -> None:
        """Additive DDL: the bridge's SCHEMAFULL table predates consumption."""
        try:
            self._sql(
                f"DEFINE FIELD IF NOT EXISTS claimed_by ON {TABLE} TYPE array<string> DEFAULT [];"
            )
        except Exception as exc:
            logger.debug("claim-field DDL skipped: %s", exc)

    def fetch_unclaimed(self, batch: int = 25) -> list[dict[str, Any]]:
        res = self._sql(
            f"SELECT * FROM {TABLE} "
            f"WHERE !array::find(claimed_by ?? [], '{self.consumer_id}') "
            f"ORDER BY timestamp ASC LIMIT {int(batch)};"
        )
        rows = res[-1].get("result") or []
        return [r for r in rows if isinstance(r, dict)]

    def claim(self, record_id: str) -> None:
        """SCP1: atomic idempotent set-insert — never SELECT-then-write."""
        if not _SAFE_RECORD_ID.match(record_id):
            raise ValueError(f"unsafe record id: {record_id!r}")
        res = self._sql(
            f"UPDATE {record_id} SET claimed_by = "
            f"array::add(claimed_by ?? [], '{self.consumer_id}');"
        )
        errs = [r for r in res if isinstance(r, dict) and r.get("status") == "ERR"]
        if errs:
            raise RuntimeError(f"claim failed for {record_id}: {errs[0].get('result')}")

    def handle(self, event: dict[str, Any]) -> dict[str, Any]:
        """Deterministic routing; local inference writes the summary only."""
        etype = str(event.get("event_type", "")).lower()
        payload = str(event.get("payload", ""))
        if etype in ACTIONABLE_EVENT_TYPES:
            summary = self._summarize(etype, payload)
            item_id = self._file_work_item(
                f"[datamesh:{etype}] {summary[:120]}",
                f"{summary}\n\nRaw event payload:\n{payload[:1200]}",
                str(event.get("source", "datamesh")),
            )
            return {"action": "work-item", "work_item": item_id}
        return {"action": "tally"}

    def run_once(self, batch: int = 25) -> dict[str, Any]:
        """One drain pass. Honest summary; per-event failures isolated."""
        summary: dict[str, Any] = {
            "consumer": self.consumer_id,
            "fetched": 0,
            "actioned": [],
            "tallied": 0,
            "failed": {},
        }
        for event in self.fetch_unclaimed(batch):
            rid = str(event.get("id", ""))
            summary["fetched"] += 1
            try:
                self.claim(rid)  # claim-before-handle: exactly-once per consumer
                outcome = self.handle(event)
                if outcome["action"] == "work-item":
                    summary["actioned"].append({"event": rid, "work_item": outcome["work_item"]})
                else:
                    summary["tallied"] += 1
            except Exception as exc:
                logger.warning("event %s failed: %s", rid, exc)
                summary["failed"][rid] = str(exc)
        return summary
