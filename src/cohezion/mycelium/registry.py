"""MyceliumRegistry — cross-agent pattern aggregator.

Subscribes to WITNESS_MARK precipitation events and clusters them by proximity
in the 12D state space + fabric breakdown similarity. When a cluster grows
past a threshold size, a MYCELIUM_PATTERN precipitation event is emitted so
downstream consumers (skill refiner, orchestrator) see the aggregate signal.

Clustering is intentionally simple (greedy nearest-cluster within radius) so
this module stays a spine component, not a research project. For heavier
clustering (DBSCAN, HDBSCAN, spectral), a future pass can swap in scikit-learn
without changing the interface.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from cohezion.precipitation.bus import PrecipitationBus, get_bus
from cohezion.precipitation.events import (
    FABRIC_DIMS,
    TWELVE_D_DIMS,
    PrecipitationEvent,
    PrecipitationKind,
)


logger = logging.getLogger(__name__)


@dataclass
class MyceliumCluster:
    """A growing set of WITNESS_MARKs clustered by 12D + fabric proximity."""

    cluster_id: str
    centroid_twelve_d: dict[str, float]
    centroid_fabric: dict[str, float]
    member_event_ids: list[str] = field(default_factory=list)
    member_agent_ids: set[str] = field(default_factory=set)
    member_universe_ids: set[str] = field(default_factory=set)
    mean_coherence: float = 0.0
    pattern_emitted: bool = False

    @property
    def size(self) -> int:
        return len(self.member_event_ids)


def _euclidean(a: dict[str, float], b: dict[str, float], dims: tuple[str, ...]) -> float:
    return math.sqrt(sum((a.get(d, 0.5) - b.get(d, 0.5)) ** 2 for d in dims))


def _update_centroid(
    centroid: dict[str, float],
    new_point: dict[str, float],
    new_size: int,
    dims: tuple[str, ...],
) -> dict[str, float]:
    """Running-mean update — O(dims)."""
    prev_size = new_size - 1
    return {d: (centroid.get(d, 0.5) * prev_size + new_point.get(d, 0.5)) / new_size for d in dims}


class MyceliumRegistry:
    """Clusters WITNESS_MARK events and emits MYCELIUM_PATTERN on threshold.

    Parameters
    ----------
    radius : float
        Max 12D Euclidean distance for a new event to be assigned to an
        existing cluster. Smaller = tighter clusters. Default 0.35 balances
        specificity and recall on the [0, 1]-bounded 12D space.
    fabric_radius : float
        Additional distance threshold on the 4-fabric breakdown. Fabric
        mismatch overrides 12D proximity (we want cross-universe patterns to
        be in the same fabric regime).
    pattern_size_threshold : int
        Minimum cluster size to emit a MYCELIUM_PATTERN event.
    """

    def __init__(
        self,
        bus: PrecipitationBus | None = None,
        *,
        radius: float = 0.35,
        fabric_radius: float = 0.2,
        pattern_size_threshold: int = 3,
    ) -> None:
        self.bus = bus or get_bus()
        self.radius = radius
        self.fabric_radius = fabric_radius
        self.pattern_size_threshold = pattern_size_threshold
        self.clusters: list[MyceliumCluster] = []

    def subscribe(self) -> None:
        self.bus.subscribe(self._on_event, kind=PrecipitationKind.WITNESS_MARK)

    def _on_event(self, event: PrecipitationEvent) -> None:
        cluster = self._find_or_create_cluster(event)
        cluster.member_event_ids.append(event.event_id)
        if event.agent_id:
            cluster.member_agent_ids.add(event.agent_id)
        cluster.member_universe_ids.add(event.universe_id)

        # Recompute mean coherence incrementally.
        n = cluster.size
        cluster.mean_coherence = (cluster.mean_coherence * (n - 1) + event.coherence) / n

        # Emit pattern event once per cluster upon crossing threshold.
        if cluster.size >= self.pattern_size_threshold and not cluster.pattern_emitted:
            cluster.pattern_emitted = True
            self._emit_pattern_event(cluster)

    def _find_or_create_cluster(self, event: PrecipitationEvent) -> MyceliumCluster:
        for cluster in self.clusters:
            d12 = _euclidean(cluster.centroid_twelve_d, event.twelve_d, TWELVE_D_DIMS)
            dfab = _euclidean(
                cluster.centroid_fabric,
                event.fabric_breakdown,
                tuple(FABRIC_DIMS.keys()),
            )
            if d12 <= self.radius and dfab <= self.fabric_radius:
                # Update centroids with running mean.
                new_size = cluster.size + 1
                cluster.centroid_twelve_d = _update_centroid(
                    cluster.centroid_twelve_d, event.twelve_d, new_size, TWELVE_D_DIMS
                )
                cluster.centroid_fabric = _update_centroid(
                    cluster.centroid_fabric,
                    event.fabric_breakdown,
                    new_size,
                    tuple(FABRIC_DIMS.keys()),
                )
                return cluster

        cluster = MyceliumCluster(
            cluster_id=f"mycelium-{len(self.clusters)}",
            centroid_twelve_d=dict(event.twelve_d),
            centroid_fabric=dict(event.fabric_breakdown),
        )
        self.clusters.append(cluster)
        return cluster

    def _emit_pattern_event(self, cluster: MyceliumCluster) -> None:
        """Fire MYCELIUM_PATTERN precipitation event for a cluster that crossed threshold.

        Also auto-promotes the pattern to:
        - the Obsidian vault at `<vault>/wiki/ouroboros/improvements/<cluster_id>.md`
        - SurrealDB at `mycelium_patterns:<cluster_id>` (ns cohezion, db main)
        Both writes are best-effort: failure logs and continues. The
        PrecipitationEvent emission is the source of truth; vault+DB are
        derived indexes for search and audit.
        """
        try:
            # Cross-universe patterns are more valuable; boost coherence slightly.
            cross_universe_boost = 0.1 if len(cluster.member_universe_ids) > 1 else 0.0
            coherence = max(0.0, min(1.0, cluster.mean_coherence + cross_universe_boost))

            self.bus.emit(
                PrecipitationEvent(
                    kind=PrecipitationKind.MYCELIUM_PATTERN,
                    universe_id="mycelium",
                    coherence=coherence,
                    twelve_d=cluster.centroid_twelve_d,
                    fabric_breakdown=cluster.centroid_fabric,
                    payload={
                        "cluster_id": cluster.cluster_id,
                        "size": cluster.size,
                        "mean_coherence": cluster.mean_coherence,
                        "agent_count": len(cluster.member_agent_ids),
                        "universe_count": len(cluster.member_universe_ids),
                        "cross_universe": len(cluster.member_universe_ids) > 1,
                        "member_event_ids": list(cluster.member_event_ids),
                    },
                )
            )
            logger.info(
                "mycelium pattern %s emitted: size=%d coherence=%.3f universes=%d",
                cluster.cluster_id,
                cluster.size,
                cluster.mean_coherence,
                len(cluster.member_universe_ids),
            )
        except Exception:
            logger.debug("Failed to emit MYCELIUM_PATTERN", exc_info=True)

        # Best-effort auto-promotion to vault + SurrealDB.
        self._promote_pattern(cluster)

    def _promote_pattern(self, cluster: MyceliumCluster) -> None:
        """Write a short markdown summary to the Obsidian vault AND a row to
        SurrealDB. Both are best-effort. Cooldown: only promote if the
        cluster spans >= 2 universes (true cross-agent signal); a single
        event from one agent does not warrant a vault entry.
        """
        # Cooldown guard: don't promote single-universe single-agent
        # clusters. Otherwise we'd write a vault note every time any
        # agent produces 3+ same-signature events.
        if len(cluster.member_universe_ids) < 2:
            logger.debug(
                "skip vault+db promotion for %s (only %d universe[s])",
                cluster.cluster_id,
                len(cluster.member_universe_ids),
            )
            return

        from datetime import UTC, datetime
        from pathlib import Path

        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        slug = cluster.cluster_id.replace(" ", "-")
        payload = {
            "cluster_id": cluster.cluster_id,
            "size": cluster.size,
            "mean_coherence": cluster.mean_coherence,
            "agent_count": len(cluster.member_agent_ids),
            "universe_count": len(cluster.member_universe_ids),
            "member_universe_ids": sorted(cluster.member_universe_ids),
            "member_agent_ids": sorted(cluster.member_agent_ids),
            "member_event_ids": list(cluster.member_event_ids),
            "cross_universe": True,
        }

        # 1) Write to Obsidian vault
        try:
            vault_root = Path(
                __import__("os").environ.get(
                    "COHEZION_VAULT_PATH",
                    "/home/mike-anderson/vaults/cohezion-vault",
                )
            )
            improvements = vault_root / "wiki" / "ouroboros" / "improvements"
            improvements.mkdir(parents=True, exist_ok=True)
            md_path = improvements / f"{slug}-{ts}.md"
            lines = [
                "---",
                f"cluster_id: {cluster.cluster_id}",
                f"date: {datetime.now(UTC).isoformat()}",
                f"size: {cluster.size}",
                f"mean_coherence: {cluster.mean_coherence:.3f}",
                f"universes: {len(cluster.member_universe_ids)}",
                f"agents: {len(cluster.member_agent_ids)}",
                "tags: [mycelium, pattern, auto-promoted]",
                "---",
                "",
                f"# Mycelium pattern: {cluster.cluster_id}",
                "",
                f"Cluster size: **{cluster.size}** events",
                f"Mean coherence: **{cluster.mean_coherence:.3f}**",
                f"Universes: {', '.join(sorted(cluster.member_universe_ids))}",
                f"Agents: {', '.join(sorted(cluster.member_agent_ids))}",
                "",
                "## Member events",
                "",
            ]
            for eid in cluster.member_event_ids:
                lines.append(f"- `{eid}`")
            lines.append("")
            md_path.write_text("\n".join(lines))
            logger.info("wrote mycelium pattern to vault: %s", md_path)
        except Exception as exc:
            logger.debug("vault write failed for %s: %s", cluster.cluster_id, exc)

        # 2) Write to SurrealDB
        try:
            import base64
            import json
            import urllib.error
            import urllib.request

            surreal_url = __import__("os").environ.get("SURREALDB_URL", "http://localhost:8001/sql")
            surreal_user = __import__("os").environ.get("SURREALDB_USER", "root")
            surreal_pass = __import__("os").environ.get("SURREALDB_PASS", "root")
            # Sanitize cluster_id for use as record ID. Also strip dashes
            # from the timestamp — SurrealDB parses `tablename:id-with-dashes`
            # as a subtraction expression, which fails type validation.
            sanitized = cluster.cluster_id.replace("-", "_").replace(" ", "_")
            ts_compact = ts.replace("-", "")  # 20260604-032226 -> 20260604032226
            db_id = f"mycelium_patterns:{sanitized}_{ts_compact}"
            payload_json = json.dumps(payload)
            created_at = datetime.now(UTC).isoformat()

            # Inline values into the SQL (safe — no user input flows here;
            # all values come from numeric fields + a JSON payload we built)
            def _sql_str(v: str) -> str:
                return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"

            upsert_sql = (
                f"UPSERT {db_id} SET "
                f"cluster_id = {_sql_str(cluster.cluster_id)}, "
                f"size = {cluster.size}, "
                f"mean_coherence = {cluster.mean_coherence}, "
                f"agent_count = {len(cluster.member_agent_ids)}, "
                f"universe_count = {len(cluster.member_universe_ids)}, "
                f"cross_universe = true, "
                f"payload = {_sql_str(payload_json)}, "
                f"created_at = {_sql_str(created_at)};"
            )
            auth = base64.b64encode(f"{surreal_user}:{surreal_pass}".encode()).decode()
            req = urllib.request.Request(
                surreal_url,
                data=upsert_sql.encode("utf-8"),
                method="POST",
                headers={
                    "surreal-ns": "cohezion",
                    "surreal-db": "main",
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "text/plain",
                },
            )
            response_bytes = urllib.request.urlopen(req, timeout=5).read()
            # SurrealDB returns 200 even on logical errors (e.g. type
            # validation). Check the response for an error status.
            try:
                response_json = json.loads(response_bytes)
                if isinstance(response_json, list) and response_json:
                    first = response_json[0]
                    if isinstance(first, dict) and first.get("status") == "ERR":
                        logger.debug(
                            "surrealdb UPSERT returned ERR for %s: %s",
                            db_id,
                            str(first.get("result", ""))[:200],
                        )
                        return
            except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                pass  # Non-JSON response, assume success (urllib raised on real error)
            logger.info("wrote mycelium pattern to surrealdb: %s", db_id)
        except (urllib.error.URLError, OSError, Exception) as exc:
            logger.debug("surrealdb write failed for %s: %s", cluster.cluster_id, exc)


__all__ = ["MyceliumCluster", "MyceliumRegistry"]
