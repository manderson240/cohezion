"""Fleet-Health Specialist — the observability role (item 36, thread E).

Composes three VERIFIED measurement tools into one snapshot, adding no new measurement logic:
  - `loop_telemetry` (item 25) — the three loops' live progress counts;
  - `marginal_power_w` (item 17) — per-lane SoC ΔP from idle/load samples;
  - `deposit_cerebellum_neuron` (item 24) — the ONE write: a stabilized routing pattern → one
    procedural-memory neuron.
  - `persistently_dropped_findings` (item 125) — verified research levers the loop keeps noticing
    but never integrates (surfaced read-only from the SAME feed/backlog the telemetry reads; no write).

Everything is read-only EXCEPT that single gated cerebellum deposit, which only fires for a
genuinely stable routing pattern and, with an injected ``store``, never touches the real graph
(and is a no-op under pytest when no store is given). The power samples and store are injectable so
the snapshot is deterministic and testable.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from cohezion.compound.loop_telemetry import LoopTelemetry, loop_telemetry
from cohezion.compound.research_feed_parser import persistently_dropped_findings
from cohezion.governance.knowledge_bridge import deposit_cerebellum_neuron
from cohezion.substrate.hardware_monitor import marginal_power_w


@dataclass(frozen=True)
class FleetHealthSnapshot:
    """One observability snapshot. ``cerebellum_deposited`` is the neuron written iff the routing
    corpus showed a stabilized pattern, else None (no write)."""

    telemetry: LoopTelemetry
    lane_power_w: dict[str, float | None]
    cerebellum_deposited: dict | None
    persistent_misses: list[
        tuple[str, list[int]]
    ]  # item 125: verified levers the loop keeps dropping


class FleetHealthSpecialist:
    """Read-only fleet observability + a single gated procedural-memory deposit."""

    def snapshot(
        self,
        *,
        routing_records: list[dict] | None = None,
        lane_power_samples: Mapping[str, tuple[Sequence[float | None], Sequence[float | None]]]
        | None = None,
        store: list[dict] | None = None,
        backlog_path: Path | None = None,
        ledger_path: Path | None = None,
        feed_path: Path | None = None,
    ) -> FleetHealthSnapshot:
        """Compose the live loop telemetry, optional per-lane marginal power, and (only on a stable
        routing pattern) a single cerebellum deposit. With an injected ``store`` the deposit lands
        there, never the real graph; with ``store=None`` under pytest it is a no-op (item 24)."""
        telemetry = loop_telemetry(
            backlog_path=backlog_path, ledger_path=ledger_path, feed_path=feed_path
        )
        lane_power: dict[str, float | None] = {}
        for lane, (idle, load) in (lane_power_samples or {}).items():
            lane_power[lane] = marginal_power_w(list(idle), list(load))
        deposited: dict | None = None
        if routing_records:
            deposited = deposit_cerebellum_neuron(routing_records, store=store)
        # Surface the research levers the loop keeps dropping (item 125) from the SAME feed/backlog
        # the telemetry already read — passing the injected paths through (no hidden default read).
        persistent_misses = persistently_dropped_findings(
            feed_path=feed_path, backlog_path=backlog_path
        )
        return FleetHealthSnapshot(
            telemetry=telemetry,
            lane_power_w=lane_power,
            cerebellum_deposited=deposited,
            persistent_misses=persistent_misses,
        )
