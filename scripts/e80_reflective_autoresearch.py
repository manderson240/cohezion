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

# Sibling-script import: O(1) last-id cache replaces O(N) full-file scans
sys.path.insert(0, str(REPO / "scripts"))
from jsonl_id_cache import bump_id, next_id  # noqa: E402
import surreal_index  # noqa: E402  (silent-fail telemetry-grade index)

# Import autoliterature helpers (it's a sibling script — load by file path)
spec = importlib.util.spec_from_file_location(
    "autolit", REPO / "scripts" / "autoliterature_scanner.py"
)
assert spec and spec.loader
autolit = importlib.util.module_from_spec(spec)
sys.modules["autolit"] = autolit
spec.loader.exec_module(autolit)


def _tail_jsonl(path, n_rows: int) -> list[str]:
    """Memory-efficient tail: seek near EOF and read forward.

    Replaces `path.read_text().splitlines()[-n_rows:]` which would load the
    entire 584 MB autoresearch.jsonl into memory just to keep the last 60 lines.
    """
    if not path.exists():
        return []
    size = path.stat().st_size
    # Heuristic: average row ~500 B; reserve 4× headroom + 16 KB minimum.
    chunk = max(16 * 1024, n_rows * 2000)
    start = max(0, size - chunk)
    with path.open("rb") as f:
        f.seek(start)
        buf = f.read()
    # If we didn't start from byte 0, drop the partial first line.
    text = buf.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    if start > 0 and lines:
        lines = lines[1:]
    if len(lines) < n_rows and start > 0:
        # Headroom guess was too small — fall back to a slightly bigger window
        # rather than a full read_text. One retry at 4× chunk is plenty.
        chunk2 = chunk * 4
        start = max(0, size - chunk2)
        with path.open("rb") as f:
            f.seek(start)
            buf = f.read()
        text = buf.decode("utf-8", errors="ignore")
        lines = text.splitlines()
        if start > 0 and lines:
            lines = lines[1:]
    return lines[-n_rows:]


def _trace_rows_via_surreal(experiment: str | None, n_rows: int) -> list[dict] | None:
    """Try SurrealDB first; return None on silent-fail (so caller uses JSONL)."""
    try:
        rows = surreal_index.query_recent(experiment=experiment, n=n_rows)
        if rows:
            return rows
    except Exception:
        pass
    return None


def build_trace(n_rows: int = 60) -> tuple[str, dict]:
    """Build compact trace + summary stats from recent autoresearch rows.

    Source preference: SurrealDB (indexed query) → JSONL tail (seeked read).
    Both stay schema-compatible: each row has status/metric/asi/description fields.
    """
    if not JSONL.exists() and surreal_index.health().get("available") is not True:
        return "", {}

    rows: list[dict] = []
    surreal_rows = _trace_rows_via_surreal(experiment=None, n_rows=n_rows)
    if surreal_rows:
        rows = surreal_rows
        source = "surreal"
    else:
        for ln in _tail_jsonl(JSONL, n_rows):
            try:
                rows.append(json.loads(ln))
            except Exception:
                pass
        source = "jsonl_tail"
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
        "source": source,
    }
    return trace, summary


def reflect_via_lane(lane: dict, trace: str) -> dict:
    """Ask a single lane: 'what experiment is missing?' Returns parsed verdict.

    E104 anti-sycophancy: pairs the generative prompt with an adversarial
    "what's wrong" prompt. A label that appears in BOTH the missing-list AND
    the wrong-list is the strongest signal — both perspectives flag it.
    """
    base_prompt = (
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
    # E109: simplified critic — single-label answer, no JSON. The structured
    # JSON critic (E106/E108) was empirically too hard for small models even
    # at max_tokens=480. Plain-text label is much easier to grade and parse.
    critic_prompt = (
        "Looking at this autoresearch trace, which experiment label appears to be "
        "OVER-INTERPRETED — where high keep-rate may be masking silent failures "
        "or trivial wins?\n\n"
        f"{trace}\n\n"
        "Reply with ONLY the label (e.g. 'E63' or 'E80') — nothing else. "
        "If no label is suspect, reply with 'NONE'."
    )

    # E109: simplified single-label critic only needs ~5-15 tokens.
    # Critic call timeout is half the lane timeout so the serial pair fits
    # under the outer 30s ThreadPoolExecutor cap (was overflowing in E108).
    txt, telem = autolit._post_chat(
        lane["model"], base_prompt, timeout=lane["timeout"], max_tokens=240,
        endpoint=lane.get("endpoint"),
    )
    crit_txt, crit_telem = autolit._post_chat(
        lane["model"], critic_prompt,
        timeout=max(5.0, lane["timeout"] / 2),
        max_tokens=20,
        endpoint=lane.get("endpoint"),
    )

    out: dict = {
        "lane": lane["name"],
        "model": lane["model"],
        "latency_ms": telem["latency_ms"],
        "critic_latency_ms": crit_telem["latency_ms"],
        "tokens_per_sec": telem["tokens_per_sec"],
        "ok": telem["ok"],
        "error_class": telem["error_class"],
    }
    # Parse the generative response
    if txt:
        m = re.search(r"\{.*\}", txt, re.DOTALL)
        if m:
            try:
                out.update(json.loads(m.group(0)))
            except Exception:
                out["raw"] = txt[:300]
        else:
            out["raw"] = txt[:300]
    # E109: parse simplified single-label critic. Looks for the FIRST E-label
    # token (E\d+) in the response. Falls back to "NONE" or the raw text.
    if crit_txt:
        clean = crit_txt.strip()
        # Match any E-label (E1, E80, E97, E1234, etc.). Case-insensitive.
        lm = re.search(r"\bE\d{1,4}\b", clean, re.IGNORECASE)
        if lm:
            suspect = lm.group(0).upper()
            out["critic"] = {"suspect_experiment": suspect, "raw": clean[:200]}
            proposed = ((out.get("proposed_experiment") or "").strip().lower())
            # Convergence: if the same label appears in both lists, strongest signal
            out["adversarial_convergence"] = bool(
                proposed and (suspect.lower() in proposed or proposed.startswith(suspect.lower()))
            )
        elif "NONE" in clean.upper()[:50]:
            out["critic"] = {"suspect_experiment": None, "raw": clean[:200]}
        else:
            out["critic_raw"] = clean[:300]
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
                v = fut.result(timeout=120.0)  # E109: was 30s — too tight for 2-call lanes
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

    # E113 anti-sycophancy: unanimous vote is suspect — re-probe with adversarial prompt.
    unanimous_flag: bool = False
    if consensus_label and consensus_count == len(verdicts) and len(verdicts) > 1:
        probe_lane = autolit.LEMONADE_LANES[0]
        adv_prompt = (
            f"The silicon council unanimously proposed '{consensus_label}'. Unanimous agreement "
            "may reflect groupthink. What would make '{consensus_label}' the WRONG next experiment? "
            "Name one alternative label from the trace that was under-weighted. "
            "Reply with ONLY that label (e.g. 'E77') or 'CONFIRMED' if you stand by the pick."
        )
        try:
            adv_txt, _ = autolit._post_chat(
                probe_lane["model"], adv_prompt,
                timeout=probe_lane["timeout"], max_tokens=20,
                endpoint=probe_lane.get("endpoint"),
            )
            if adv_txt:
                lm = re.search(r"\bE\d{1,4}\b", adv_txt.strip(), re.IGNORECASE)
                if lm and lm.group(0).lower() != consensus_label:
                    unanimous_flag = True
                    print(f"[e80] ⚠️  UNANIMOUS DIVERGENCE: re-probe suggests "
                          f"'{lm.group(0).upper()}' vs unanimous '{consensus_label}'", flush=True)
        except Exception:
            pass  # non-blocking

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
    new_id = next_id(VAULT_OBS, "id")
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
           "text": "\n".join(text_parts),
           "experiment": "E80"}
    with VAULT_OBS.open("a") as f:
        f.write(json.dumps(obs) + "\n")
    bump_id(VAULT_OBS, new_id, "id")
    print(f"\n[e80] saved vault observation #{new_id}", flush=True)

    # autoresearch.jsonl
    new_run = next_id(JSONL, "run")
    # E104 silent-abort guard: structural V-Model invariant. If we have NO
    # successful lane verdicts AND no distinct proposals AND metric=0, this
    # row represents a SILENT FAILURE (council fired but produced nothing
    # parseable) — not a "keep". Logging it as "keep" would inflate the
    # kept-rate that future E80 traces interpret as "we're succeeding".
    n_ok_lanes = sum(1 for v in verdicts if v.get("ok"))
    n_proposals = len(distinct_proposals)
    if n_ok_lanes == 0 and n_proposals == 0:
        run_status = "silent_abort"
    elif n_proposals > 0:
        run_status = "keep"
    else:
        run_status = "discard"
    # Aggregate adversarial-convergence signal (E104 part-a)
    n_adversarial_convergence = sum(1 for v in verdicts if v.get("adversarial_convergence"))
    suspect_labels = [(v.get("critic") or {}).get("suspect_experiment")
                      for v in verdicts if v.get("ok")]
    suspect_labels = [s for s in suspect_labels if s]
    # E113 anti-sycophancy #3: unanimous-vote warning. When ALL responsive lanes
    # converge on the same label, that's *suspect* — disagreement is signal,
    # consensus may be groupthink. Flag it; downstream scripts can re-fire with
    # sharpened prompt + temperature=0.7 to test whether the consensus survives.
    is_unanimous = (n_ok_lanes >= 3
                    and consensus_label is not None
                    and consensus_count == n_ok_lanes)
    requires_dissent_check = is_unanimous
    entry = {
        "run": new_run, "metric": float(n_proposals),
        "metrics": {
            "trace_rows_analyzed": summary["rows_analyzed"],
            "experiment_labels_in_trace": summary["labels_count"],
            "lanes_fired": len(verdicts),
            "lanes_ok": n_ok_lanes,
            "distinct_proposals": n_proposals,
            "consensus_label": consensus_label,
            "consensus_count": consensus_count,
            "adversarial_convergence_lanes": n_adversarial_convergence,
            "suspect_labels_voted": suspect_labels,
            "unanimous_warning": is_unanimous,
            "unanimous_divergence": unanimous_flag,
            "requires_dissent_check": requires_dissent_check,
            "proposals": distinct_proposals,
            "per_lane_verdicts": verdicts,
            "elapsed_s": round(elapsed, 2),
            "silent_abort_guard": "active",
        },
        "status": run_status,
        "description": f"E80 reflective autoresearch (E104-anti-sycophancy): "
                       f"{n_proposals} novel proposals "
                       f"({consensus_count}/{len(verdicts)} consensus on '{consensus_label}'); "
                       f"adversarial convergence={n_adversarial_convergence}/{len(verdicts)}; "
                       f"suspect labels={suspect_labels[:3]}; status={run_status}",
        "timestamp": int(time.time() * 1000), "segment": 99, "confidence": 1.0,
        "asi": {"experiment": "E80", "novel_proposals": n_proposals,
                "consensus_label": consensus_label, "consensus_count": consensus_count,
                "adversarial_convergence_lanes": n_adversarial_convergence,
                "suspect_labels": suspect_labels,
                "unanimous_warning": is_unanimous,
                "requires_dissent_check": requires_dissent_check},
    }
    with JSONL.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    bump_id(JSONL, new_run, "run")
    # Dual-write to SurrealDB index (silent-fails if v3 protocol issue persists)
    surreal_index.record_experiment_run({
        "run": new_run,
        "experiment": "E80",
        "status": entry["status"],
        "metric": entry["metric"],
        "ts": entry["timestamp"],
        "asi": entry["asi"],
        "description": entry["description"],
    })
    print(f"[e80] appended autoresearch.jsonl run #{new_run}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
