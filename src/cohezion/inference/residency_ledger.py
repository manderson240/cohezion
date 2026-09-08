"""Write-through residency ledger — the degraded-mode fallback for model residency.

Why this exists (measured 2026-08-03): model residency is observable through exactly ONE
endpoint, ``/api/v1/health``. ``/api/v1/models`` reports ``downloaded`` (on disk, not in
RAM) and ``/api/v1/system-info`` reports neither. And ``/health`` is the endpoint that
stops answering under the memory pressure the hotswap gate exists to relieve — measured
HTTP 000 at 12s and 20s while ``/models`` answered in 3ms.

``hotswap.resident_models()`` returns ``[]`` on any such failure. An empty resident list
means an empty VICTIM list, so ``ensure_resident`` cannot evict anything and refuses
forever: fail-closed, therefore safe, and therefore useless — the "gate that can only
refuse" shape.

The ledger does NOT replace the server view. hotswap's original design note is right:
local bookkeeping drifts the moment anything else loads a model (measured: the fleet
churned three times in one session, and today two models this session never requested
appeared resident). So:

* the SERVER is authoritative whenever it answers,
* the LEDGER is the fallback only when the server answers nothing,
* drift is REPORTED rather than silently reconciled — ``reconcile()`` never mutates.

One asymmetry is deliberate and load-bearing: an empty server list is treated as "no
information", never as "the fleet is empty". Reading a health failure as an empty fleet
would wipe the very fallback this module exists to provide.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReconcileReport:
    """Drift between what this process believes and what the server reports."""

    only_in_ledger: list[str]
    only_in_server: list[str]
    agreed: list[str]

    @property
    def in_sync(self) -> bool:
        return not self.only_in_ledger and not self.only_in_server


@dataclass
class ResidencyLedger:
    """Records every load/unload this process performs.

    Entries are health-shaped so callers can consume them interchangeably with
    ``/api/v1/health`` rows.
    """

    _entries: dict[str, dict] = field(default_factory=dict)
    _seq: int = 0

    def record_load(self, model_id: str, weights_gb: float | None = None) -> None:
        self._seq += 1
        self._entries[model_id] = {
            "model_name": model_id,
            "loaded": True,
            "is_busy": False,
            "last_use": self._seq,
            "weights_gb": weights_gb,
        }

    def record_unload(self, model_id: str) -> None:
        """Forget a model. Unknown ids are a no-op — an unload we did not originate
        (or a retry) must not raise."""
        self._entries.pop(model_id, None)

    def touch(self, model_id: str) -> None:
        """Mark a model as most-recently-used, so LRU eviction order stays honest for
        models that are being SERVED but not re-loaded."""
        entry = self._entries.get(model_id)
        if entry is not None:
            self._seq += 1
            entry["last_use"] = self._seq

    def entries(self) -> list[dict]:
        """Health-shaped rows, NEWEST-USED FIRST.

        Ordering is load-bearing: ``hotswap.ensure_resident`` picks victims from
        ``reversed(loaded)``, so reversing this would evict the most recently used model.
        """
        return sorted(self._entries.values(), key=lambda e: e["last_use"], reverse=True)

    def reconcile(self, server_entries: list[dict]) -> ReconcileReport:
        """Compare against the server. Pure — never mutates (see ``adopt``)."""
        server = {m.get("model_name", "") for m in server_entries if m.get("model_name")}
        mine = set(self._entries)
        return ReconcileReport(
            only_in_ledger=sorted(mine - server),
            only_in_server=sorted(server - mine),
            agreed=sorted(mine & server),
        )

    def adopt(self, server_entries: list[dict]) -> None:
        """Replace the ledger with the server's view — the drift repair.

        An EMPTY server list is ignored. It means "health told us nothing", which is
        indistinguishable at this layer from a degraded endpoint, and adopting it would
        erase the fallback exactly when it is needed.
        """
        if not server_entries:
            logger.debug("residency_ledger: empty server view — keeping ledger as-is")
            return
        rebuilt: dict[str, dict] = {}
        seq = 0
        for m in reversed(server_entries):  # server is newest-first; replay oldest-first
            name = m.get("model_name")
            if not name:
                continue
            seq += 1
            rebuilt[name] = {
                "model_name": name,
                "loaded": True,
                "is_busy": bool(m.get("is_busy")),
                "last_use": seq,
                "weights_gb": self._entries.get(name, {}).get("weights_gb"),
            }
        self._entries = rebuilt
        self._seq = seq


def resident_view(server_entries: list[dict], ledger: ResidencyLedger | None) -> list[dict]:
    """Best available residency view: the server when it answers, else the ledger.

    Returning the server list whenever it is non-empty preserves hotswap's correct
    design choice (ground truth beats local bookkeeping). Falling back only on an EMPTY
    server list is what keeps eviction possible while ``/health`` is degraded.
    """
    if server_entries:
        return server_entries
    if ledger is None:
        return []
    fallback = ledger.entries()
    if fallback:
        logger.info(
            "residency_ledger: server view empty — falling back to %d ledger entr%s",
            len(fallback),
            "y" if len(fallback) == 1 else "ies",
        )
    return fallback
