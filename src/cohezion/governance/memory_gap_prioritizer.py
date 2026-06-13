"""Memory gap prioritizer — rank knowledge gaps by routing frequency.

Backlog item 129: When the system routes a request to a domain but has low memory
(vault entries, cached results) for that domain, we have a "memory gap". Gaps that
occur on HIGH-FREQUENCY routing paths are more expensive (every miss is a cloud call)
than gaps on rare paths.

This module ranks gaps by: gap_score = routing_frequency × (1 - memory_coverage)

Where:
  routing_frequency = fraction of all requests routed to this domain in the window
  memory_coverage   = min(1.0, vault_entries / target_entries)

Gaps with gap_score > 0.1 are candidates for proactive vault seeding.

Composes:
  - item 75: routing-record schema (domain routing counts)
  - routing-records: domain → request count map from TieredOrchestrator telemetry
"""

from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)

_ALERT_THRESHOLD = 0.1
_DEFAULT_TARGET_ENTRIES = 5  # vault entries per domain to consider "covered"


@dataclass
class MemoryGap:
    """A knowledge gap ranked by its impact on routing performance.

    Attributes:
        domain: The routing domain (e.g. 'code', 'reason', 'summarize').
        routing_frequency: Fraction of requests routed to this domain in the window.
        vault_entries: Number of relevant vault entries found for this domain.
        memory_coverage: vault_entries / target_entries, capped at 1.0.
        gap_score: routing_frequency × (1 - memory_coverage). Higher = more urgent.
        alert: True if gap_score exceeds the alert threshold.
    """

    domain: str
    routing_frequency: float
    vault_entries: int
    memory_coverage: float
    gap_score: float
    alert: bool


def prioritize_memory_gaps(
    routing_counts: dict[str, int],
    vault_entry_counts: dict[str, int],
    target_entries_per_domain: int = _DEFAULT_TARGET_ENTRIES,
) -> list[MemoryGap]:
    """Rank domains by memory gap urgency.

    Args:
        routing_counts: Dict mapping domain name to request count in the window.
            Example: {'code': 120, 'reason': 45, 'classify': 210}.
        vault_entry_counts: Dict mapping domain name to vault entry count.
            Example: {'code': 3, 'reason': 0, 'classify': 8}.
        target_entries_per_domain: Number of vault entries to consider a domain
            "fully covered". Gaps below this count inflate gap_score.

    Returns:
        List of MemoryGap objects sorted by gap_score descending (most urgent first).
    """
    total_requests = max(sum(routing_counts.values()), 1)
    domains = set(routing_counts) | set(vault_entry_counts)

    gaps: list[MemoryGap] = []
    for domain in domains:
        count = routing_counts.get(domain, 0)
        freq = count / total_requests
        entries = vault_entry_counts.get(domain, 0)
        coverage = min(1.0, entries / target_entries_per_domain)
        score = freq * (1.0 - coverage)
        gaps.append(
            MemoryGap(
                domain=domain,
                routing_frequency=freq,
                vault_entries=entries,
                memory_coverage=coverage,
                gap_score=score,
                alert=score > _ALERT_THRESHOLD,
            )
        )

    return sorted(gaps, key=lambda g: (-g.gap_score, g.domain))


def gap_report(gaps: list[MemoryGap]) -> str:
    """Human-readable memory gap priority report."""
    alerts = [g for g in gaps if g.alert]
    lines = [
        f"Memory Gap Priority Report — {len(gaps)} domains",
        f"Urgent gaps (score>{_ALERT_THRESHOLD}): {len(alerts)}",
        "",
        f"{'Domain':<20} {'Freq':>7} {'Entries':>7} {'Coverage':>9} {'Score':>8} {'!':>2}",
        "-" * 60,
    ]
    for g in gaps:
        flag = "⚠" if g.alert else ""
        lines.append(
            f"{g.domain:<20} {g.routing_frequency:>7.2%} {g.vault_entries:>7d}"
            f" {g.memory_coverage:>9.2%} {g.gap_score:>8.4f} {flag:>2}"
        )
    if alerts:
        lines += [
            "",
            "Recommended vault seeding:",
            *[
                f"  • {g.domain}: add {_DEFAULT_TARGET_ENTRIES - g.vault_entries} entries"
                for g in alerts
            ],
        ]
    return "\n".join(lines)
