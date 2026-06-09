"""Durable usage sink — the persistent record that makes inference spend monitorable.

``TokenUsageRecord`` (``token_budget.py``) computes asymmetric local-vs-cloud cost, but it
is an in-memory, process-lifetime singleton: when the process exits, the numbers are gone,
and there is no cross-session / cross-harness corpus to monitor against a budget.

This module is the missing sink. It mirrors ``models.routing_log`` exactly:

* **fail-soft** — a write error NEVER breaks the dispatch path (returns None);
* **pytest-skipped** — a path-less call under pytest/unittest no-ops, so the suite never
  pollutes the real corpus (inject ``path`` to test the write);
* **append-JSONL** — one line per dispatch at ``~/.cohezion-research/logs/usage_log.jsonl``.

``summarize_usage`` is the read side the monitor surfaces: local-vs-cloud tokens, cloud $,
and the headline ``local_fraction`` KPI (the share of tokens served by free AMD silicon).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_LOG = Path.home() / ".cohezion-research" / "logs" / "usage_log.jsonl"


def record_usage(
    *,
    model: str,
    lane: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    local: bool,
    energy_usd: float = 0.0,
    cached: bool = False,
    source: str = "live",
    ts: str | None = None,
    path: Path | None = None,
) -> dict | None:
    """Append one usage record. Returns the written dict, or None if skipped/failed.

    ``local`` is the writer's authoritative free-silicon flag (lane-derived) — the
    aggregator trusts it rather than re-deriving from cost, so a $0 *cached cloud* hit is
    never miscounted as local. ``cost_usd`` is the cloud API charge ($0 for local);
    ``energy_usd`` is the LOCAL electricity charge ($0 for cloud, which draws no local
    watts). Skips silently (returns None) under pytest without an explicit ``path``.
    Never raises.
    """
    try:
        import sys

        if path is None and ("pytest" in sys.modules or "unittest" in sys.modules):
            return None
        rec: dict[str, object] = {
            "ts": ts or datetime.now(UTC).isoformat(),
            "model": model,
            "lane": lane,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "cost_usd": float(cost_usd),
            "energy_usd": round(float(energy_usd), 9),
            "local": bool(local),
            "cached": bool(cached),
            "source": source,
        }
        sink = path or DEFAULT_LOG
        sink.parent.mkdir(parents=True, exist_ok=True)
        with sink.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        return rec
    except Exception:
        return None


_CLOUD_PREFIXES = ("claude-", "gemini-", "gpt-", "anthropic/", "google/")

# Local silicon power draw by lane, in watts. Canonical source: model_registry._LANE_WATTS
# (duplicated here as a stable physical constant to keep this low-level sink dependency-free).
_LANE_WATTS = {"npu": 2.0, "igpu_rocwmma": 35.0, "igpu_unified": 35.0, "cpu": 55.0}
_DEFAULT_LOCAL_WATTS = 35.0  # unknown local lane → assume iGPU (the common generation tier)


def estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 chars (GPT/Claude convention). Minimum 1."""
    return max(1, len(text or "") // 4)


def electricity_rate_usd_per_kwh() -> float:
    """Local electricity price; override via ``COHEZION_ELECTRICITY_USD_PER_KWH``.

    Default 0.17 ≈ 2026 US residential average ($/kWh). Local silicon is not free — this
    is what turns 'local (free)' into the true marginal cost of an NPU/iGPU/CPU dispatch.
    """
    import os

    try:
        return float(os.environ.get("COHEZION_ELECTRICITY_USD_PER_KWH", "0.17"))
    except (TypeError, ValueError):
        return 0.17


def _infer_local_watts(model: str, lane: str | None) -> float:
    """Best-effort power draw for a local dispatch: prefer the explicit lane, else infer
    the tier from the model id (FLM/sub-1B → NPU; 26B+/70B → CPU; otherwise iGPU)."""
    if lane and lane in _LANE_WATTS:
        return _LANE_WATTS[lane]
    m = (model or "").lower()
    if "flm" in m or "-1b" in m or "0.6b" in m or "1b-" in m:
        return _LANE_WATTS["npu"]
    if "31b" in m or "26b" in m or "70b" in m:
        return _LANE_WATTS["cpu"]
    return _DEFAULT_LOCAL_WATTS


def estimate_energy_usd(watts: float, latency_ms: float) -> float:
    """Electricity cost of a dispatch: watts × duration × rate. Zero for non-positive inputs."""
    if watts <= 0 or latency_ms <= 0:
        return 0.0
    kwh = watts * (latency_ms / 1000.0) / 3600.0 / 1000.0
    return kwh * electricity_rate_usd_per_kwh()


def record_dispatch(
    *,
    prompt: str,
    text: str,
    model: str,
    cost_usd: float,
    latency_ms: float = 0.0,
    lane: str | None = None,
    source: str = "orchestrator",
    cached: bool = False,
    path: Path | None = None,
) -> dict | None:
    """Convenience over :func:`record_usage` for the dispatch chokepoints.

    Estimates tokens from prompt/text and classifies the lane robustly: a dispatch is
    *cloud* if it cost money OR the model id is a known cloud prefix (so a $0 *cached*
    cloud hit still lands in the cloud bucket, not miscounted as free local silicon).
    For local dispatches it also charges electricity (watts × latency × rate); cloud
    dispatches draw ~0 LOCAL watts, so their ``energy_usd`` is 0.
    """
    is_cloud = cost_usd > 0.0 or any((model or "").lower().startswith(p) for p in _CLOUD_PREFIXES)
    energy_usd = (
        0.0 if is_cloud else estimate_energy_usd(_infer_local_watts(model, lane), latency_ms)
    )
    return record_usage(
        model=model or "unknown",
        lane=lane or ("cloud" if is_cloud else "local"),
        input_tokens=estimate_tokens(prompt),
        output_tokens=estimate_tokens(text),
        cost_usd=float(cost_usd),
        energy_usd=energy_usd,
        local=not is_cloud,
        cached=cached,
        source=source,
        path=path,
    )


def read_usage(
    *,
    since: str | None = None,
    source: str | None = None,
    path: Path | None = None,
) -> list[dict]:
    """Load usage records, optionally filtered by ISO ``since`` timestamp and/or ``source``."""
    sink = path or DEFAULT_LOG
    if not sink.exists():
        return []
    out: list[dict] = []
    for rec in _iter_lines(sink):
        if since is not None and str(rec.get("ts", "")) < since:
            continue
        if source is not None and rec.get("source") != source:
            continue
        out.append(rec)
    return out


def _iter_lines(sink: Path) -> Iterator[dict]:
    with sink.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


@dataclass(frozen=True)
class UsageSummary:
    """Aggregated usage across a set of records. ``local_fraction`` is the headline KPI."""

    local_tokens: int = 0
    cloud_input_tokens: int = 0
    cloud_output_tokens: int = 0
    cloud_cost_usd: float = 0.0
    local_energy_usd: float = 0.0
    n_records: int = 0
    n_cached: int = 0
    by_model: dict[str, dict] = field(default_factory=dict)

    @property
    def cloud_tokens(self) -> int:
        return self.cloud_input_tokens + self.cloud_output_tokens

    @property
    def total_tokens(self) -> int:
        return self.local_tokens + self.cloud_tokens

    @property
    def total_cost_usd(self) -> float:
        """True total marginal cost: cloud API spend + local electricity."""
        return self.cloud_cost_usd + self.local_energy_usd

    @property
    def local_fraction(self) -> float:
        """Share of total tokens served by local silicon. Token-weighted, not record-count."""
        total = self.total_tokens
        return self.local_tokens / total if total else 0.0


def summarize_usage(records: list[dict]) -> UsageSummary:
    """Aggregate raw usage records into a :class:`UsageSummary` (token-weighted)."""
    local_tokens = 0
    cloud_in = 0
    cloud_out = 0
    cloud_cost = 0.0
    local_energy = 0.0
    n_cached = 0
    by_model: dict[str, dict] = {}

    for rec in records:
        in_tok = int(rec.get("input_tokens", 0) or 0)
        out_tok = int(rec.get("output_tokens", 0) or 0)
        cost = float(rec.get("cost_usd", 0.0) or 0.0)
        energy = float(rec.get("energy_usd", 0.0) or 0.0)
        is_local = bool(rec.get("local"))
        if rec.get("cached"):
            n_cached += 1

        local_energy += energy
        if is_local:
            local_tokens += in_tok + out_tok
        else:
            cloud_in += in_tok
            cloud_out += out_tok
            cloud_cost += cost

        model = str(rec.get("model", "") or "unknown")
        slot = by_model.setdefault(
            model, {"calls": 0, "tokens": 0, "cost_usd": 0.0, "energy_usd": 0.0}
        )
        slot["calls"] += 1
        slot["tokens"] += in_tok + out_tok
        slot["cost_usd"] = round(slot["cost_usd"] + cost, 9)
        slot["energy_usd"] = round(slot["energy_usd"] + energy, 9)

    return UsageSummary(
        local_tokens=local_tokens,
        cloud_input_tokens=cloud_in,
        cloud_output_tokens=cloud_out,
        cloud_cost_usd=round(cloud_cost, 9),
        local_energy_usd=round(local_energy, 9),
        n_records=len(records),
        n_cached=n_cached,
        by_model=by_model,
    )


def format_report(summary: UsageSummary, *, budget_usd: float | None = None) -> str:
    """Render a compact, human-readable usage report. The ``local_fraction`` KPI leads."""
    lines = [
        "── Cohezion inference usage ──",
        f"local:         {summary.local_tokens:,} tokens  "
        f"(electricity ~${summary.local_energy_usd:.4f})",
        f"cloud (paid):  {summary.cloud_tokens:,} tokens "
        f"({summary.cloud_input_tokens:,} in / {summary.cloud_output_tokens:,} out)",
        f"cloud spend:   ${summary.cloud_cost_usd:.4f}  (API)",
        f"TOTAL cost:    ${summary.total_cost_usd:.4f}  (cloud API + local electricity)",
        f"local share:   {summary.local_fraction:.1%}  (KPI — higher = cheaper)",
        f"dispatches:    {summary.n_records}  (cache hits: {summary.n_cached})",
    ]
    if budget_usd is not None:
        remaining = budget_usd - summary.cloud_cost_usd
        pct = (summary.cloud_cost_usd / budget_usd * 100) if budget_usd else 0.0
        lines.append(
            f"cloud budget:  ${summary.cloud_cost_usd:.4f} / ${budget_usd:.2f} used "
            f"({pct:.1f}%) — ${remaining:.5f} remaining"
        )
    if summary.by_model:
        lines.append("by model:")
        for model, agg in sorted(
            summary.by_model.items(),
            key=lambda kv: -(kv[1]["cost_usd"] + kv[1].get("energy_usd", 0.0)),
        ):
            spend = agg["cost_usd"] + agg.get("energy_usd", 0.0)
            lines.append(
                f"  {model:<28} {agg['calls']:>4} calls  {agg['tokens']:>9,} tok  ${spend:.4f}"
            )
    return "\n".join(lines)
