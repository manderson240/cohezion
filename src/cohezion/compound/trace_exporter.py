"""Phoenix/OpenTelemetry trace exporter for Cohezion execution traces.

Converts Cohezion telemetry and retrospection trace dicts to OpenTelemetry-style
spans for ingestion by Arize Phoenix (/v1/traces) or any OTEL-compatible collector.

Supported input formats:
  - CompoundTelemetry JSON  (fields: request_id, skill_name, timestamp, success,
                              total_latency_ms, steps[])
  - RetrospectionSummary dict (fields: cycle_id, skill_name, coherence_delta,
                                success, timestamp)

No external dependencies — pure stdlib dataclasses + hashlib.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class OtelSpan:
    """OpenTelemetry-compatible span representation."""

    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start_time_ms: float
    end_time_ms: float
    attributes: dict[str, str | float | int]
    status: str  # "OK" | "ERROR"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _hex_id(seed: str, length: int = 16) -> str:
    """Deterministic hex ID from a seed string. No randomness, no uuid import."""
    return hashlib.sha256(seed.encode()).hexdigest()[:length]


def _parse_start_ms(trace_dict: dict[str, Any]) -> float:
    """Extract execution start time as Unix milliseconds from a trace dict.

    Handles:
      - float/int fields (already epoch seconds or ms)
      - ISO-8601 string "timestamp" field
    """
    ts = trace_dict.get("timestamp")
    if ts is None:
        return 0.0
    if isinstance(ts, (int, float)):
        # Heuristic: epoch seconds are <1e12; epoch ms are >=1e12
        return float(ts) * 1000.0 if ts < 1e12 else float(ts)
    # ISO-8601 string
    try:
        dt = datetime.fromisoformat(str(ts))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.timestamp() * 1000.0
    except ValueError:
        return 0.0


def _resolve_trace_id(trace_dict: dict[str, Any]) -> str:
    """Return the best available trace ID from a trace dict.

    Priority: cycle_id > request_id > generated fallback.
    """
    return (
        trace_dict.get("cycle_id")
        or trace_dict.get("request_id")
        or _hex_id(str(trace_dict.get("skill_name", "unknown")), 32)
    )


def _root_status(trace_dict: dict[str, Any]) -> str:
    return "OK" if trace_dict.get("success", True) else "ERROR"


def _step_status(step: dict[str, Any]) -> str:
    return "ERROR" if step.get("error") else "OK"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def execution_trace_to_otel_spans(trace_dict: dict) -> list[OtelSpan]:
    """Convert a Cohezion execution trace dict to OpenTelemetry span format.

    Compatible with Phoenix ingestion via /v1/traces endpoint.

    Parameters
    ----------
    trace_dict:
        A dict produced by CompoundTelemetry.write_metrics() or
        RetrospectionSummary.to_dict().  Unknown fields are silently ignored.

    Returns
    -------
    list[OtelSpan]
        A non-empty list: the first element is always the root span for the
        whole execution; subsequent elements are child spans, one per step.
        If the trace has no ``steps`` array an empty child list is returned
        (root-only trace).
    """
    trace_id = _resolve_trace_id(trace_dict)
    skill_name: str = trace_dict.get("skill_name") or "compound.execution"
    start_ms: float = _parse_start_ms(trace_dict)
    total_ms: float = float(trace_dict.get("total_latency_ms", 0.0))

    # Root span coherence_delta: prefer top-level field, else infer from steps
    steps: list[dict[str, Any]] = trace_dict.get("steps", [])
    if "coherence_delta" in trace_dict:
        root_coherence_delta: float = float(trace_dict["coherence_delta"])
    elif steps:
        first_coh = float(steps[0].get("coherence", 0.0))
        last_coh = float(steps[-1].get("coherence", 0.0))
        root_coherence_delta = last_coh - first_coh
    else:
        root_coherence_delta = 0.0

    root_span_id = _hex_id(trace_id)

    root_attrs: dict[str, str | float | int] = {
        "cohezion.coherence_delta": root_coherence_delta,
        "cohezion.skill_name": skill_name,
    }
    if "total_tokens_in" in trace_dict:
        root_attrs["cohezion.tokens_in"] = int(trace_dict["total_tokens_in"])
    if "total_tokens_out" in trace_dict:
        root_attrs["cohezion.tokens_out"] = int(trace_dict["total_tokens_out"])

    root = OtelSpan(
        trace_id=trace_id,
        span_id=root_span_id,
        parent_span_id=None,
        name=skill_name,
        start_time_ms=start_ms,
        end_time_ms=start_ms + total_ms,
        attributes=root_attrs,
        status=_root_status(trace_dict),
    )

    spans: list[OtelSpan] = [root]

    # Build child spans from the steps array
    cursor_ms = start_ms
    prev_coherence: float | None = None

    for i, step in enumerate(steps):
        step_name: str = step.get("step_name") or f"step_{i}"
        latency: float = float(step.get("latency_ms", 0.0))
        step_span_id = _hex_id(f"{trace_id}:{step_name}:{i}")

        coherence_now = float(step.get("coherence", 0.0))
        coherence_delta = coherence_now - (
            prev_coherence if prev_coherence is not None else coherence_now
        )
        prev_coherence = coherence_now

        child_attrs: dict[str, str | float | int] = {
            "cohezion.coherence_delta": coherence_delta,
            "cohezion.coherence": coherence_now,
            "cohezion.tokens_in": int(step.get("tokens_in", 0)),
            "cohezion.tokens_out": int(step.get("tokens_out", 0)),
            "cohezion.cache_hit": int(bool(step.get("cache_hit", False))),
        }
        if step.get("error"):
            child_attrs["cohezion.error"] = str(step["error"])

        spans.append(
            OtelSpan(
                trace_id=trace_id,
                span_id=step_span_id,
                parent_span_id=root_span_id,
                name=step_name,
                start_time_ms=cursor_ms,
                end_time_ms=cursor_ms + latency,
                attributes=child_attrs,
                status=_step_status(step),
            )
        )
        cursor_ms += latency

    return spans


## FUTURE HOOKS
# - Add OTLP/HTTP export: `export_spans_to_phoenix(spans, endpoint)` using
#   `urllib.request` (no httpx dependency) when Phoenix URL is configured.
# - Wire into CompoundTelemetry.write_metrics() as an optional side-channel.
# - Support batch export accumulator for high-throughput compound loops.
# - Add W3C TraceContext header generation for distributed trace propagation.
