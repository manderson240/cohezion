"""E80: GEPA-style reflective AutoresearchEngine via silicon council.

The existing cohezion.compound.autoresearch.AutoresearchEngine has produced
the same 2 recommendations for 1733 cycles (E74 finding). E76 identified
GEPA (arXiv 2507.19457, ICLR 2026 oral) as the canonical fix: feed the
*full execution trace* to LLMs and let them reflect.

This script wires that. It:
  1. Pulls the last N keep/discard rows from autoresearch.jsonl
  2. Builds a compact trace string (description + status + metric per row)
  3. Asks each silicon lane (NPU + iGPU + CPU in parallel) to propose
     ONE concrete new experiment hypothesis the loop hasn't tried
  4. Aggregates the 3 verdicts; the union of *novel* proposals beats the
     single recycled "cache: increase semantic_cache_size" output today
  5. Persists to vault (type="reflection") and autoresearch.jsonl

Reuses helpers from scripts/autoliterature_scanner.py via direct import.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import time
import timeit
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path


REPO = Path("/home/mike-anderson/dev/cohezion")
JSONL = REPO / "autoresearch.jsonl"
VAULT_OBS = Path("/home/mike-anderson/vaults/cohezion-vault/memory/observations.jsonl")

# Import autoliterature helpers (it's a sibling script — load by file path)
spec = importlib.util.spec_from_file_location(
    "autolit", REPO / "scripts" / "autoliterature_scanner.py"
)
assert spec and spec.loader
autolit = importlib.util.module_from_spec(spec)
sys.modules["autolit"] = autolit
spec.loader.exec_module(autolit)


def build_trace(n_rows: int = 60) -> tuple[str, dict]:
    """Read tail of autoresearch.jsonl, build compact trace + summary stats."""
    if not JSONL.exists():
        return "", {}
    lines = JSONL.read_text().splitlines()[-n_rows:]
    rows: list[dict] = []
    for ln in lines:
        try:
            rows.append(json.loads(ln))
        except Exception:
            pass
    keep_n = sum(1 for r in rows if r.get("status") == "keep")
    discard_n = sum(1 for r in rows if r.get("status") == "discard")
    # Group by experiment label
    by_exp: dict[str, list[dict]] = {}
    for r in rows:
        label = r.get("asi", {}).get("experiment", "?")
        by_exp.setdefault(label, []).append(r)

    trace_lines: list[str] = []
    for label in sorted(by_exp.keys()):
        rs = by_exp[label]
        kept = sum(1 for r in rs if r.get("status") == "keep")
        avg_metric = sum(float(r.get("metric", 0) or 0) for r in rs) / max(1, len(rs))
        # Take 1 representative description per experiment label
        rep = rs[0].get("description", "")[:90]
        trace_lines.append(
            f"  [{label}] n={len(rs)} kept={kept} avg_metric={avg_metric:.3f}  → {rep}"
        )

    trace = (
        f"Recent autoresearch trace ({len(rows)} rows, "
        f"{keep_n} kept, {discard_n} discarded):\n" + "\n".join(trace_lines)
    )
    summary = {
        "rows_analyzed": len(rows),
        "kept": keep_n,
        "discarded": discard_n,
        "experiment_labels": sorted(by_exp.keys()),
        "labels_count": len(by_exp),
    }
    return trace, summary


def reflect_via_lane(lane: dict, trace: str) -> dict:
    """Ask a single lane: 'what experiment is missing?' Returns parsed verdict."""
    prompt = (
        "You are reviewing an autonomous research loop's recent trace. "
        "Most experiments succeed (high keep rate) which suggests the loop is exploring "
        "an already-saturated region. Propose ONE concrete new experiment that "
        "would actually push the system into unexplored territory.\n\n"
        f"{trace}\n\n"
        "Output ONLY JSON: "
        '{"proposed_experiment": "<short label>", '
        '"hypothesis": "<one sentence>", '
        '"why_novel": "<one sentence on why this is NOT redundant with the trace above>", '
        '"unblocks": "<one open problem this targets>"}'
    )
    txt, telem = autolit._post_chat(
        lane["model"], prompt, timeout=lane["timeout"], max_tokens=240
    )
    out: dict = {
        "lane": lane["name"],
        "model": lane["model"],
        "latency_ms": telem["latency_ms"],
        "tokens_per_sec": telem["tokens_per_sec"],
        "ok": telem["ok"],
        "error_class": telem["error_class"],
    }
    if not txt:
        return out
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if not m:
        out["raw"] = txt[:300]
        return out
    try:
        parsed = json.loads(m.group(0))
        out.update(parsed)
    except Exception:
        out["raw"] = txt[:300]
    return out


def main() -> int:
    t0 = timeit.default_timer()
    trace, summary = build_trace(n_rows=60)
    if not trace:
        print("[e80] no trace data — aborting")
        return 1

    print(f"[e80] trace built: {summary['rows_analyzed']} rows, "
          f"{summary['labels_count']} unique experiment labels", flush=True)

    profile = autolit._load_silicon_profile()
    profile["runs"] = profile.get("runs", 0) + 1

    print("[e80] firing silicon council in parallel (NPU + iGPU + CPU)...", flush=True)
    verdicts: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(autolit.LEMONADE_LANES)) as pool:
        futures = {pool.submit(reflect_via_lane, lane, trace): lane
                   for lane in autolit.LEMONADE_LANES}
        for fut in as_completed(futures):
            try:
                v = fut.result(timeout=30.0)
                # Update silicon_profile telemetry
                autolit._update_silicon_profile(profile, v["lane"], {
                    "latency_ms": v["latency_ms"],
                    "ok": v.get("ok", False),
                    "error_class": v.get("error_class"),
                    "tokens_per_sec": v.get("tokens_per_sec", 0),
                    "response_tokens": 0,
                })
                verdicts.append(v)
            except Exception as exc:
                lane_name = futures[fut]["name"]
                verdicts.append({"lane": lane_name, "ok": False, "error_class": str(exc)})

    autolit._save_silicon_profile(profile)

    # Aggregate: collect distinct (proposed_experiment, hypothesis) pairs across lanes
    distinct_proposals: list[dict] = []
    seen_labels: set[str] = set()
    for v in verdicts:
        if not v.get("ok"):
            continue
        label = (v.get("proposed_experiment") or "").strip().lower()
        if not label or label in seen_labels:
            continue
        seen_labels.add(label)
        distinct_proposals.append({
            "proposed_experiment": v.get("proposed_experiment"),
            "hypothesis": v.get("hypothesis"),
            "why_novel": v.get("why_novel"),
            "unblocks": v.get("unblocks"),
            "voted_by_lane": v["lane"],
        })

    # If a label is proposed by 2+ lanes, that's stronger consensus
    label_count: dict[str, int] = {}
    for v in verdicts:
        if not v.get("ok"):
            continue
        lab = (v.get("proposed_experiment") or "").strip().lower()
        if lab:
            label_count[lab] = label_count.get(lab, 0) + 1
    consensus_label = max(label_count, key=label_count.get) if label_count else None
    consensus_count = label_count.get(consensus_label, 0) if consensus_label else 0

    elapsed = timeit.default_timer() - t0

    # Print
    print(f"\n[e80] silicon council done in {elapsed:.1f}s — "
          f"{len(verdicts)} lanes responded, {len(distinct_proposals)} distinct proposals",
          flush=True)
    print(f"[e80] consensus label: '{consensus_label}' (voted by {consensus_count}/{len(verdicts)} lanes)",
          flush=True)
    for i, p in enumerate(distinct_proposals, 1):
        print(f"\n  Proposal {i} (from {p['voted_by_lane']}):")
        print(f"    label: {p['proposed_experiment']}")
        print(f"    hypothesis: {p['hypothesis']}")
        print(f"    why novel: {p['why_novel']}")
        print(f"    unblocks: {p['unblocks']}")

    # Persist to vault as type="reflection"
    last_id = 0
    for line in VAULT_OBS.read_text().splitlines():
        try:
            last_id = max(last_id, json.loads(line).get("id", 0))
        except Exception:
            pass
    new_id = last_id + 1
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    text_parts = [
        f"E80 reflective autoresearch via silicon council. Analyzed {summary['rows_analyzed']} "
        f"trace rows ({summary['kept']} kept, {summary['discarded']} discarded across "
        f"{summary['labels_count']} experiment labels). Fired NPU + iGPU + CPU in parallel; "
        f"{len(verdicts)} lanes responded ({sum(1 for v in verdicts if v.get('ok'))} ok). "
        f"Consensus label: '{consensus_label}' ({consensus_count}/{len(verdicts)} lane votes).",
        f"\nDistinct proposals ({len(distinct_proposals)}):"
    ]
    for i, p in enumerate(distinct_proposals, 1):
        text_parts.append(
            f"  {i}. [{p['voted_by_lane']}] {p['proposed_experiment']}: "
            f"{p['hypothesis']} (unblocks: {p['unblocks']})"
        )
    text_parts.append(
        f"\nThis replaces the existing AutoresearchEngine's stuck output ('cache: increase "
        f"semantic_cache_size to 4096' — repeated 1733 cycles per E74). Wall time {elapsed:.1f}s."
    )
    obs = {"id": new_id, "timestamp": ts, "type": "reflection", "project": "cohezion",
           "title": f"E80 reflective autoresearch: {len(distinct_proposals)} novel proposals via silicon council "
                    f"(consensus: {consensus_label})",
           "text": "\n".join(text_parts)}
    with VAULT_OBS.open("a") as f:
        f.write(json.dumps(obs) + "\n")
    print(f"\n[e80] saved vault observation #{new_id}", flush=True)

    # autoresearch.jsonl
    last_run = 0
    for line in JSONL.read_text().splitlines():
        try:
            last_run = max(last_run, json.loads(line).get("run", 0))
        except Exception:
            pass
    entry = {
        "run": last_run + 1, "metric": float(len(distinct_proposals)),
        "metrics": {
            "trace_rows_analyzed": summary["rows_analyzed"],
            "experiment_labels_in_trace": summary["labels_count"],
            "lanes_fired": len(verdicts),
            "lanes_ok": sum(1 for v in verdicts if v.get("ok")),
            "distinct_proposals": len(distinct_proposals),
            "consensus_label": consensus_label,
            "consensus_count": consensus_count,
            "proposals": distinct_proposals,
            "per_lane_verdicts": verdicts,
            "elapsed_s": round(elapsed, 2),
        },
        "status": "keep" if distinct_proposals else "discard",
        "description": f"E80 reflective autoresearch: {len(distinct_proposals)} novel proposals via "
                       f"silicon council ({consensus_count}/{len(verdicts)} consensus on '{consensus_label}')",
        "timestamp": int(time.time() * 1000), "segment": 99, "confidence": 1.0,
        "asi": {"experiment": "E80", "novel_proposals": len(distinct_proposals),
                "consensus_label": consensus_label, "consensus_count": consensus_count},
    }
    with JSONL.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[e80] appended autoresearch.jsonl run #{last_run + 1}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
