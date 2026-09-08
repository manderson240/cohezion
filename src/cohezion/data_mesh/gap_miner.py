"""Gap miner — turns repeated GaiaDataAgent actions into proactive work-queue items.

The reactive half of datamesh improvement already runs: GaiaAgentRoster agents
answer quality alerts with HEAL/ALERT/ENRICH follow-on CUSTOM events, which the
DataMeshEventBridge persists to SurrealDB. But a domain that triggers the same
action over and over is signalling a MISSING capability (context, schema, doc,
detector) that no single event fixes — the "conversation gap mining" idea from
LangChain's agent-first data stack (2026-07-27 blog), adapted to our event bus.

This module mines those repeats: group persisted GaiaDataAgent CUSTOM events by
(domain, action) over a window; any group at/over threshold becomes ONE
work-queue item (Kanban-first discipline). Products marked ``endorsed`` on
their owner domain rank their gaps higher — the curator trust signal consumed.

Wiring target (Wire-at-Creation): compound_daemon._datamesh_improvement_pass
calls ``GapMiner.run_once()`` after the roster pass; CLI entry
``python -m cohezion.data_mesh.gap_miner`` for cron. Checkpoint at
``~/.cohezion/gap_miner_state.json`` makes reruns idempotent.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from pathlib import Path
from typing import Any

from cohezion.data_mesh.data_product import DataProduct


logger = logging.getLogger(__name__)

GAP_THRESHOLD = 3  # same (domain, action) this many times in the window = a gap
WINDOW_S = 7 * 86400

_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Accept": "application/json",
    "Authorization": "Basic cm9vdDpyb290",
}
_WORK_QUEUE_API = "http://localhost:8080/api/work-queue"
_WORK_QUEUE_FILE = Path.home() / ".cohezion" / "work-queue.json"
_STATE_FILE = Path.home() / ".cohezion" / "gap_miner_state.json"


class GapMiner:
    """Mine repeated roster actions into work-queue items. Fail-open everywhere."""

    def __init__(
        self,
        *,
        products: dict[str, DataProduct] | None = None,
        threshold: int = GAP_THRESHOLD,
        window_s: float = WINDOW_S,
        state_file: Path = _STATE_FILE,
    ) -> None:
        self._products = products or {}
        self._threshold = threshold
        self._window_s = window_s
        self._state_file = state_file

    # ── persistence of "already filed" ────────────────────────────────────────

    def _load_state(self) -> dict[str, Any]:
        try:
            return json.loads(self._state_file.read_text())
        except Exception:
            return {"filed": []}

    def _save_state(self, state: dict[str, Any]) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(state))
        except Exception as exc:
            logger.debug("gap_miner: state save failed: %s", exc)

    # ── event query ───────────────────────────────────────────────────────────

    def _fetch_events(self, since_ts: float) -> list[dict[str, Any]]:
        sql = (
            f"SELECT source, payload, timestamp FROM data_product_event "
            f"WHERE event_type = 'CUSTOM' AND timestamp > {since_ts} "
            f"AND string::starts_with(source, 'GaiaDataAgent/');"
        )
        try:
            req = urllib.request.Request(_SURREAL_URL, data=sql.encode(), headers=_SURREAL_HEADERS)
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                results = json.loads(resp.read())
            rows = results[-1].get("result", []) if isinstance(results, list) else []
        except Exception as exc:
            logger.debug("gap_miner: event fetch failed: %s", exc)
            return []
        out = []
        for row in rows:
            payload = row.get("payload")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {}
            row["payload"] = payload or {}
            out.append(row)
        return out

    # ── mining ────────────────────────────────────────────────────────────────

    def _domain_endorsed(self, domain: str) -> bool:
        # getattr: tolerate catalogs from trees that predate the endorsed field
        # (mixed-tree daemon deployments load this module ahead of data_product).
        return any(
            p.owner_domain == domain and getattr(p, "endorsed", False)
            for p in self._products.values()
        )

    def mine(self, since_ts: float | None = None) -> list[dict[str, Any]]:
        """Group events by (domain, action); return gap dicts at/over threshold."""
        since = since_ts if since_ts is not None else time.time() - self._window_s
        groups: dict[tuple[str, str], int] = {}
        for ev in self._fetch_events(since):
            payload = ev["payload"]
            domain = payload.get("domain") or ev.get("source", "").split("/")[-1]
            action = payload.get("action", "UNKNOWN")
            groups[(domain, action)] = groups.get((domain, action), 0) + 1
        gaps = []
        for (domain, action), count in sorted(groups.items(), key=lambda kv: -kv[1]):
            if count < self._threshold:
                continue
            endorsed = self._domain_endorsed(domain)
            gaps.append(
                {
                    "id": f"gap-{domain}-{action.lower()}",
                    "type": "datamesh-gap",
                    "domain": domain,
                    "action": action,
                    "count": count,
                    "endorsed_domain": endorsed,
                    # Endorsed domains are curator-marked sources of truth — their
                    # recurring gaps outrank same-count gaps elsewhere.
                    "priority": ("high" if endorsed else "normal"),
                    "title": f"Datamesh gap: {domain} needed {action} x{count} in window",
                    "status": "pending_review",
                }
            )
        return gaps

    # ── filing ────────────────────────────────────────────────────────────────

    def _push(self, item: dict[str, Any]) -> bool:
        try:  # API first
            req = urllib.request.Request(
                _WORK_QUEUE_API,
                data=json.dumps(item).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=4):  # noqa: S310
                return True
        except Exception:
            pass
        try:  # file fallback
            q = json.loads(_WORK_QUEUE_FILE.read_text()) if _WORK_QUEUE_FILE.exists() else {}
            items = q.setdefault("items", [])
            items.append(item)
            _WORK_QUEUE_FILE.write_text(json.dumps(q, indent=1))
            return True
        except Exception as exc:
            logger.debug("gap_miner: push failed: %s", exc)
            return False

    def run_once(self, since_ts: float | None = None) -> dict[str, Any]:
        """Mine and file new gaps (idempotent across runs via filed-id state)."""
        state = self._load_state()
        filed: list[str] = list(state.get("filed", []))
        gaps = self.mine(since_ts)
        new = [g for g in gaps if g["id"] not in filed]
        pushed = 0
        for gap in new:
            if self._push(gap):
                filed.append(gap["id"])
                pushed += 1
                logger.info("gap_miner: filed %s (count=%d)", gap["id"], gap["count"])
        self._save_state({"filed": filed[-500:]})
        return {"gaps_found": len(gaps), "filed": pushed}


def make_gap_miner() -> GapMiner:
    """Factory with the registered product catalog (endorsement source)."""
    try:
        from cohezion.data_mesh.data_product import get_cohezion_data_products

        products = get_cohezion_data_products()
    except Exception:
        products = {}
    return GapMiner(products=products)


def main() -> None:  # pragma: no cover - thin CLI shim
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(make_gap_miner().run_once(), indent=1))


if __name__ == "__main__":  # pragma: no cover
    main()
